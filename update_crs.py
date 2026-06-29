import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set

from supabase import Client, create_client


SCORE_KEY_RE = re.compile(r"^s(\d{2})s(\d{2})$")
SPECIAL_SCORE_MAP = {
    "s1sh": "胜其他",
    "s1sd": "平其他",
    "s1sa": "负其他",
}
SKIP_CRS_KEYS = {"goalLine", "goalLineValue", "updateDate", "updateTime"}


def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inject CRS match data into Supabase table crs_match_info."
    )
    parser.add_argument(
        "input_json",
        help="Path to source JSON file, e.g. data_record/gamble_record_xxx.json",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("SUPABASE_URL", ""),
        help="Supabase project URL (or use SUPABASE_URL env var).",
    )
    parser.add_argument(
        "--key",
        default=os.getenv("SUPABASE_KEY", ""),
        help="Supabase key (or use SUPABASE_KEY env var).",
    )
    parser.add_argument(
        "--table",
        default="crs_match_info",
        help="Target table name (default: crs_match_info).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview rows to insert without writing to database.",
    )
    return parser.parse_args()


def create_supabase_client(url: str, key: str) -> Client:
    if not url or not key:
        raise ValueError("Missing Supabase credentials: --url/--key or env vars.")
    return create_client(url, key)


def decode_score_key(key: str) -> str:
    if key in SPECIAL_SCORE_MAP:
        return SPECIAL_SCORE_MAP[key]
    match = SCORE_KEY_RE.match(key)
    if not match:
        return key
    home = int(match.group(1))
    away = int(match.group(2))
    return f"{home}:{away}"


def normalize_crs(crs_obj: Dict[str, str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in crs_obj.items():
        if key in SKIP_CRS_KEYS or key.endswith("f"):
            continue
        if key in SPECIAL_SCORE_MAP or SCORE_KEY_RE.match(key):
            normalized[decode_score_key(key)] = value
    return normalized


def iter_matches(payload: dict) -> Iterable[dict]:
    for day in payload.get("value", {}).get("matchInfoList", []):
        for match in day.get("subMatchList", []):
            yield match


def build_insert_rows(payload: dict) -> List[dict]:
    rows: List[dict] = []
    for match in iter_matches(payload):
        match_id = match.get("matchId")
        match_date = str(match.get("matchDate", "")).strip()
        match_clock = str(match.get("matchTime", "")).strip()
        if match_id is None or not match_date or not match_clock:
            continue

        rows.append(
            {
                "match_id": int(match_id),
                "match_time": f"{match_date} {match_clock}",
                "match_category": match.get("leagueAbbName", ""),
                "match_home_team": match.get("homeTeamAbbName", ""),
                "match_away_team": match.get("awayTeamAbbName", ""),
                "crs": normalize_crs(match.get("crs") or {}),
            }
        )
    return rows


def fetch_existing_match_ids(client: Client, table: str) -> Set[int]:
    existing: Set[int] = set()
    page_size = 1000
    start = 0
    while True:
        end = start + page_size - 1
        response = (
            client.table(table)
            .select("match_id")
            .range(start, end)
            .execute()
        )
        rows = response.data or []
        for item in rows:
            try:
                existing.add(int(item["match_id"]))
            except (TypeError, ValueError, KeyError):
                continue
        if len(rows) < page_size:
            break
        start += page_size
    return existing


def main() -> None:
    load_dotenv_file(Path(".env"))
    args = parse_args()
    input_path = Path(args.input_json)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    rows = build_insert_rows(payload)
    if not rows:
        print("No valid match rows found in input JSON.")
        return

    client = create_supabase_client(args.url, args.key)
    existing_ids = fetch_existing_match_ids(client, args.table)

    to_insert = [row for row in rows if row["match_id"] not in existing_ids]
    skipped = len(rows) - len(to_insert)

    print(f"Parsed rows: {len(rows)}")
    print(f"Existing rows skipped: {skipped}")
    print(f"Rows to insert: {len(to_insert)}")

    if args.dry_run:
        print("Dry run enabled, no database writes performed.")
        return

    if not to_insert:
        print("Nothing new to insert.")
        return

    client.table(args.table).insert(to_insert).execute()
    print(f"Inserted rows: {len(to_insert)}")


if __name__ == "__main__":
    main()
