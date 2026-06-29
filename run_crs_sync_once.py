import argparse
import json
import os
import time
from pathlib import Path

from record_gamble_crs import build_output_path, fetch_crs_data, fetch_crs_data_via_curl
from update_crs import (
    build_insert_rows,
    create_supabase_client,
    fetch_existing_match_ids,
    load_dotenv_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one-shot CRS sync: fetch JSON, save file, and update Supabase."
    )
    parser.add_argument(
        "--output-dir",
        default="data_record",
        help="Directory to save JSON file (default: data_record).",
    )
    parser.add_argument(
        "--tz",
        default="Asia/Shanghai",
        help="IANA timezone used in output filename (default: Asia/Shanghai).",
    )
    parser.add_argument(
        "--table",
        default="crs_match_info",
        help="Supabase table name (default: crs_match_info).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Max attempts for fetch retry (default: 3).",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Seconds to wait between retries (default: 2.0).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write to DB, only print insert stats.",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("SUPABASE_URL", ""),
        help="Supabase URL (or use SUPABASE_URL env var / .env).",
    )
    parser.add_argument(
        "--key",
        default=os.getenv("SUPABASE_KEY", ""),
        help="Supabase key (or use SUPABASE_KEY env var / .env).",
    )
    return parser.parse_args()


def fetch_payload_with_retry(retries: int, retry_delay: float) -> dict:
    retries = max(retries, 1)
    payload = None
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            payload = fetch_crs_data()
            break
        except Exception as primary_err:
            last_error = primary_err
            try:
                payload = fetch_crs_data_via_curl()
                print("Primary fetch failed, fallback to curl succeeded.")
                break
            except Exception as curl_err:
                last_error = RuntimeError(
                    f"Primary error: {primary_err}; curl fallback error: {curl_err}"
                )

            if attempt < retries:
                print(
                    f"Fetch attempt {attempt}/{retries} failed: {last_error}. Retrying..."
                )
                time.sleep(max(retry_delay, 0.0))

    if payload is None:
        raise RuntimeError(f"Fetch failed after {retries} attempts: {last_error}")

    return payload


def main() -> None:
    load_dotenv_file(Path(".env"))
    args = parse_args()

    payload = fetch_payload_with_retry(args.retries, args.retry_delay)

    output_path = build_output_path(args.output_dir, args.tz)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved JSON: {output_path}")

    rows = build_insert_rows(payload)
    if not rows:
        print("No valid match rows found in payload.")
        return

    if not args.url or not args.key:
        raise SystemExit("Missing Supabase credentials: set .env or pass --url/--key")

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
