from datetime import datetime, timezone

from mnq_fractal_bot.data.csv_loader import load_candles_from_csv
from mnq_fractal_bot.models.candle import Candle


def main():
    print("=" * 40)
    print("MNQ FRACTAL BOT")
    print("=" * 40)
    print("Environment: PAPER")
    print("Status: STARTING")
    print("Broker connection: DISABLED")
    print("Live orders: DISABLED")
    print("=" * 40)

    candle = Candle(
        timestamp=datetime(2026, 10, 9, 13, 45, tzinfo=timezone.utc),
        open=31210.00,
        high=31235.25,
        low=31202.50,
        close=31228.75,
        volume=4850,
    )

    print()
    print("SAMPLE MNQ CANDLE")
    print(f"Time:   {candle.timestamp}")
    print(f"Open:   {candle.open}")
    print(f"High:   {candle.high}")
    print(f"Low:    {candle.low}")
    print(f"Close:  {candle.close}")
    print(f"Volume: {candle.volume}")

    candles = load_candles_from_csv(
        "data/sample_mnq_5m.csv"
    )

    print()
    print("CSV DATA TEST")
    print(f"Candles loaded: {len(candles)}")

    for csv_candle in candles:
        print(
            csv_candle.timestamp,
            csv_candle.open,
            csv_candle.high,
            csv_candle.low,
            csv_candle.close,
            csv_candle.volume,
        )


if __name__ == "__main__":
    main()