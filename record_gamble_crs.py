import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


API_URL = (
    "https://webapi.sporttery.cn/gateway/uniform/football/"
    "getMatchCalculatorV1.qry?channel=c&poolCode=crs"
)

HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "origin": "https://m.sporttery.cn",
    "referer": "https://m.sporttery.cn/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
}


def fetch_crs_data() -> dict:
    request = Request(API_URL, headers=HEADERS, method="GET")
    with urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
    if not body.strip():
        raise ValueError("Empty response body from API.")
    return json.loads(body)


def fetch_crs_data_via_curl() -> dict:
    curl_bin = shutil.which("curl") or shutil.which("curl.exe")
    if not curl_bin:
        raise RuntimeError("curl is not available in PATH.")

    command = [curl_bin, "-sS", API_URL]
    for header_key, header_value in HEADERS.items():
        command.extend(["-H", f"{header_key}: {header_value}"])

    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    body = result.stdout.strip()
    if not body:
        raise ValueError("Empty response body from curl API request.")
    return json.loads(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch CRS odds and save to JSON.")
    parser.add_argument(
        "--output-dir",
        default="data_record",
        help="Directory to save JSON file (default: data_record).",
    )
    parser.add_argument(
        "--tz",
        default="Asia/Shanghai",
        help="IANA timezone name for output filename timestamp (default: Asia/Shanghai).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Max attempts when API request fails (default: 3).",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Seconds to wait between retries (default: 2.0).",
    )
    return parser.parse_args()


def build_output_path(output_dir: str, tz_name: str) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Windows filename does not allow ":"; use "-" for time separators.
    timestamp = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H-%M-%S")
    filename = f"gamble_record_{timestamp}.json"
    return output_dir / filename


def main() -> None:
    args = parse_args()
    retries = max(args.retries, 1)
    payload = None
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            payload = fetch_crs_data()
            break
        except (HTTPError, URLError, json.JSONDecodeError, ValueError) as err:
            last_error = err
            try:
                payload = fetch_crs_data_via_curl()
                print("Primary fetch failed, fallback to curl succeeded.")
                break
            except Exception as curl_err:
                last_error = RuntimeError(
                    f"Primary error: {err}; curl fallback error: {curl_err}"
                )
            if attempt < retries:
                print(
                    f"Fetch attempt {attempt}/{retries} failed: {last_error}. Retrying..."
                )
                time.sleep(max(args.retry_delay, 0.0))

    if payload is None:
        raise SystemExit(f"Fetch failed after {retries} attempts: {last_error}")

    try:
        output_path = build_output_path(args.output_dir, args.tz)
    except Exception as err:
        raise SystemExit(f"Invalid timezone '{args.tz}': {err}") from err

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")
    # Machine-readable output for CI workflows.
    print(f"SAVED_JSON={output_path.as_posix()}")


if __name__ == "__main__":
    main()
