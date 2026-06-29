import argparse
import json
import re
from html import escape
from pathlib import Path


SCORE_KEY_RE = re.compile(r"^s(\d{2})s(\d{2})$")
SPECIAL_SCORE_MAP = {
    "s1sh": "胜其他",
    "s1sd": "平其他",
    "s1sa": "负其他",
}


def decode_score_key(key: str) -> tuple[str, int, int, int]:
    if key == "s1sh":
        return SPECIAL_SCORE_MAP[key], 0, 99, 99
    if key == "s1sd":
        return SPECIAL_SCORE_MAP[key], 1, 99, 99
    if key == "s1sa":
        return SPECIAL_SCORE_MAP[key], 2, 99, 99

    match = SCORE_KEY_RE.match(key)
    if not match:
        return key, 4, 999, 999

    home = int(match.group(1))
    away = int(match.group(2))
    if home > away:
        bucket = 0
    elif home == away:
        bucket = 1
    else:
        bucket = 2
    return f"{home}:{away}", bucket, home, away


def build_match_tiles(match: dict, match_index: int) -> str:
    crs = match.get("crs") or {}
    rows = []

    for key, odd in crs.items():
        is_standard_score = SCORE_KEY_RE.match(key) is not None
        is_special_score = key in SPECIAL_SCORE_MAP
        if not (is_standard_score or is_special_score):
            continue

        score_label, bucket, home, away = decode_score_key(key)
        rows.append((bucket, home, away, score_label, odd, key))

    rows.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

    grouped_tiles = {0: [], 1: [], 2: []}
    for bucket, _, __, score_label, odd, score_key in rows:
        if bucket not in grouped_tiles:
            continue
        grouped_tiles[bucket].append(
            "<button class='score-tile' "
            f"data-match-index='{match_index}' data-score-key='{escape(score_key)}' type='button'>"
            "<span class='counter'></span>"
            f"<span class='score'>{escape(score_label)}</span>"
            f"<span class='odd'>{escape(str(odd))}</span>"
            "</button>"
        )

    return (
        "<div class='result-line home-win-line'>"
        + "\n".join(grouped_tiles[0])
        + "</div>"
        + "<div class='result-line draw-line'>"
        + "\n".join(grouped_tiles[1])
        + "</div>"
        + "<div class='result-line away-win-line'>"
        + "\n".join(grouped_tiles[2])
        + "</div>"
    )


def build_page(data: dict) -> str:
    blocks = []
    match_index = 0
    for day in data.get("value", {}).get("matchInfoList", []):
        for match in day.get("subMatchList", []):
            title = (
                f"{match.get('matchNumStr', '')} | "
                f"{match.get('homeTeamAbbName', '')} vs {match.get('awayTeamAbbName', '')}"
            )
            meta = (
                f"{match.get('businessDate', '')} {match.get('matchTime', '')} "
                f"| {match.get('leagueAllName', '')} | matchId={match.get('matchId', '')}"
            )
            tiles_html = build_match_tiles(match, match_index)
            blocks.append(
                "<section class='card'>"
                f"<h2>{escape(title)}</h2>"
                f"<p class='meta'>{escape(meta)}</p>"
                f"<div class='tile-grid'>{tiles_html}</div>"
                "</section>"
            )
            match_index += 1

    body = "\n".join(blocks) if blocks else "<p>没有可展示的比赛数据。</p>"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>比分赔率</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
      margin: 20px;
      background: #f6f8fb;
      color: #1f2937;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
    }}
    .card {{
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 14px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }}
    .card h2 {{
      margin: 0 0 6px;
      font-size: 18px;
    }}
    .meta {{
      margin: 0 0 10px;
      color: #6b7280;
      font-size: 13px;
    }}
    .tile-grid {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .result-line {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 8px;
      min-height: 0;
    }}
    .score-tile {{
      position: relative;
      border: 1px solid #d1d5db;
      background: #ffffff;
      border-radius: 8px;
      padding: 10px 8px 8px;
      text-align: left;
      cursor: pointer;
      min-height: 68px;
      transition: background 0.15s ease;
    }}
    .score-tile .counter {{
      position: absolute;
      right: 6px;
      top: 4px;
      font-size: 12px;
      line-height: 1;
      font-weight: 700;
      color: #111827;
      display: none;
    }}
    .score-tile .score {{
      display: block;
      color: #000000;
      font-size: 18px;
      font-weight: 700;
      margin-top: 6px;
    }}
    .score-tile .odd {{
      display: block;
      margin-top: 4px;
      color: #6b7280;
      font-size: 13px;
    }}
    .score-tile.count-1 {{
      background: #fecaca;
    }}
    .score-tile.count-2 {{
      background: #fde68a;
    }}
    .score-tile.count-3 {{
      background: #86efac;
    }}
    @media (max-width: 900px) {{
      .result-line {{
        grid-template-columns: repeat(4, minmax(100px, 1fr));
      }}
    }}
    @media (max-width: 700px) {{
      .result-line {{
        grid-template-columns: repeat(3, minmax(90px, 1fr));
      }}
    }}
  </style>
</head>
<body>
  <h1>比分赔率</h1>
  {body}
  <script>
    (() => {{
      const countersByMatch = new Map();
      const tiles = Array.from(document.querySelectorAll(".score-tile"));

      function setTileCount(tile, count) {{
        tile.dataset.count = String(count);
        tile.classList.remove("count-1", "count-2", "count-3");
        if (count >= 1 && count <= 3) {{
          tile.classList.add(`count-${{count}}`);
        }}
        const counter = tile.querySelector(".counter");
        if (!counter) return;
        if (count <= 0) {{
          counter.style.display = "none";
          counter.textContent = "";
          return;
        }}
        counter.style.display = "inline";
        counter.textContent = String(count);
      }}

      function resetMatch(matchIndex) {{
        const matchCounters = countersByMatch.get(matchIndex);
        if (!matchCounters) return;
        for (const [scoreKey] of matchCounters) {{
          matchCounters.set(scoreKey, 0);
        }}
        tiles
          .filter((tile) => tile.dataset.matchIndex === matchIndex)
          .forEach((tile) => setTileCount(tile, 0));
      }}

      function getMatchTotal(matchCounters) {{
        let total = 0;
        for (const value of matchCounters.values()) {{
          total += value;
        }}
        return total;
      }}

      for (const tile of tiles) {{
        const matchIndex = tile.dataset.matchIndex || "";
        const scoreKey = tile.dataset.scoreKey || "";
        if (!countersByMatch.has(matchIndex)) {{
          countersByMatch.set(matchIndex, new Map());
        }}
        countersByMatch.get(matchIndex).set(scoreKey, 0);
        setTileCount(tile, 0);

        tile.addEventListener("click", () => {{
          const matchCounters = countersByMatch.get(matchIndex);
          if (!matchCounters) return;
          const next = (matchCounters.get(scoreKey) || 0) + 1;
          matchCounters.set(scoreKey, next);

          if (getMatchTotal(matchCounters) > 3) {{
            resetMatch(matchIndex);
            return;
          }}
          setTileCount(tile, next);
        }});
      }}
    }})();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an HTML page from CRS JSON.")
    parser.add_argument("input_json", help="Input JSON file path")
    parser.add_argument(
        "-o",
        "--output",
        default="crs_odds_view.html",
        help="Output HTML file path (default: crs_odds_view.html)",
    )
    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_path = Path(args.output)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    html_text = build_page(data)
    output_path.write_text(html_text, encoding="utf-8")
    print(f"Saved HTML: {output_path}")


if __name__ == "__main__":
    main()
