from pathlib import Path

import pandas as pd

from mnq_fractal_bot.models.candle import Candle


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def load_candles_from_csv(file_path: str | Path) -> list[Candle]:
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"CSV file does not exist: {file_path}"
        )

    df = pd.read_csv(file_path)

    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing_columns)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    candles: list[Candle] = []

    for row in df.itertuples(index=False):
        candle = Candle(
            timestamp=row.timestamp.to_pydatetime(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=int(row.volume),
        )

        candles.append(candle)

    return candles