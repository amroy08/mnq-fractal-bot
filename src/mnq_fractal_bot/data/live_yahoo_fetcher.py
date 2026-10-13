import csv
import datetime
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def fetch_live_mnq_candles(
    interval: str = "5m",
    range_period: str = "5d",
    output_path: Path | str = "data/mnq_5m_live.csv",
) -> Path:
    """
    Downloads real-time MNQ=F 5-minute futures candles directly from Yahoo Finance API
    without third-party dependencies, formatted for MNQ Fractal Bot.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/MNQ=F?interval={interval}&range={range_period}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    chart_res = data.get("chart", {}).get("result", [])
    if not chart_res:
        raise ValueError(f"No chart data returned from Yahoo Finance API for MNQ=F: {data}")

    result = chart_res[0]
    timestamps = result.get("timestamp", [])
    indicators = result.get("indicators", {})
    quote = indicators.get("quote", [{}])[0]

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    rows = []
    for i, ts in enumerate(timestamps):
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if i < len(volumes) else None

        # Filter null candles (market halt/empty intervals)
        if any(x is None for x in (o, h, l, c)):
            continue

        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        ts_str = dt.strftime("%Y-%m-%d %H:%M:%S+00:00")
        vol = int(v) if v is not None else 0
        rows.append([ts_str, f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", vol])

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)

    logger.info(f"Saved {len(rows)} live MNQ candles to {output_file}")
    return output_file


if __name__ == "__main__":
    out = fetch_live_mnq_candles()
    print(f"Successfully fetched live MNQ data into: {out}")
