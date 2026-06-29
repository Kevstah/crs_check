import json
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
    return json.loads(body)


def build_output_path() -> Path:
    output_dir = Path("data_record")
    output_dir.mkdir(parents=True, exist_ok=True)
    # Windows filename does not allow ":"; use "-" for time separators.
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    filename = f"gamble_record_{timestamp}.json"
    return output_dir / filename


def main() -> None:
    try:
        payload = fetch_crs_data()
    except HTTPError as err:
        raise SystemExit(f"HTTP error: {err.code} {err.reason}") from err
    except URLError as err:
        raise SystemExit(f"Network error: {err.reason}") from err
    except json.JSONDecodeError as err:
        raise SystemExit(f"Invalid JSON response: {err}") from err

    output_path = build_output_path()
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
