from datetime import timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf


DEFAULT_TICKER = "MNQ=F"
DEFAULT_INTERVAL = "5m"
DEFAULT_PERIOD = "60d"

DEFAULT_OUTPUT_PATH = Path(
    "data/mnq_5m_real.csv"
)


def download_mnq_data(
    ticker: str = DEFAULT_TICKER,
    interval: str = DEFAULT_INTERVAL,
    period: str = DEFAULT_PERIOD,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Download recent MNQ futures candles from Yahoo Finance
    and save them in the exact format expected by our bot:

        timestamp
        open
        high
        low
        close
        volume
    """

    output_path = Path(
        output_path
    )

    print("=" * 60)
    print("MNQ HISTORICAL DATA DOWNLOADER")
    print("=" * 60)

    print(
        f"Ticker   : {ticker}"
    )

    print(
        f"Interval : {interval}"
    )

    print(
        f"Period   : {period}"
    )

    print()

    print(
        "Downloading data..."
    )

    df = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df.empty:
        raise RuntimeError(
            "Yahoo Finance returned no MNQ data."
        )

    # ==================================================
    # YFINANCE CAN RETURN MULTI-INDEX COLUMNS
    #
    # Example:
    #
    # Price       Open High Low Close Volume
    # Ticker      MNQ=F ...
    #
    # Convert that into normal columns.
    # ==================================================

    if isinstance(
        df.columns,
        pd.MultiIndex,
    ):
        ticker_levels = (
            df.columns.get_level_values(
                -1
            )
        )

        if ticker in ticker_levels:
            df = df.xs(
                ticker,
                axis=1,
                level=-1,
                drop_level=True,
            )
        else:
            df.columns = (
                df.columns
                .get_level_values(0)
            )

    # ==================================================
    # RESET DATETIME INDEX
    # ==================================================

    df = df.reset_index()

    # yfinance may call it:
    #
    # Datetime
    # Date
    #
    # We simply rename the first column.
    first_column = (
        df.columns[0]
    )

    df = df.rename(
        columns={
            first_column: "timestamp",
        }
    )

    # ==================================================
    # NORMALIZE COLUMN NAMES
    # ==================================================

    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in df.columns
    ]

    required_columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Downloaded data is missing "
            f"columns: {missing}"
        )

    # Keep ONLY what our bot needs.
    df = df[
        required_columns
    ].copy()

    # ==================================================
    # TIMESTAMPS -> UTC
    # ==================================================

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    # ==================================================
    # NUMERIC CLEANING
    # ==================================================

    price_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in price_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["volume"] = pd.to_numeric(
        df["volume"],
        errors="coerce",
    )

    # Remove broken rows.
    df = df.dropna(
        subset=price_columns
    )

    # Missing volume is safer as zero
    # than deleting an otherwise valid candle.
    df["volume"] = (
        df["volume"]
        .fillna(0)
        .astype(int)
    )

    # ==================================================
    # DATA QUALITY
    # ==================================================

    df = (
        df
        .sort_values("timestamp")
        .drop_duplicates(
            subset=["timestamp"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    # Remove impossible OHLC candles.
    valid_ohlc = (
        (df["high"] >= df["low"])
        & (df["high"] >= df["open"])
        & (df["high"] >= df["close"])
        & (df["low"] <= df["open"])
        & (df["low"] <= df["close"])
    )

    invalid_count = (
        (~valid_ohlc).sum()
    )

    if invalid_count > 0:
        print(
            f"Removing {invalid_count} "
            "invalid OHLC rows."
        )

        df = (
            df[valid_ohlc]
            .reset_index(drop=True)
        )

    # ==================================================
    # REMOVE CURRENT INCOMPLETE 5-MINUTE BAR
    #
    # Yahoo timestamps normally represent
    # the START of the candle.
    #
    # Example:
    #
    # candle timestamp = 15:55 UTC
    # candle completes = 16:00 UTC
    #
    # If current time is still before 16:00,
    # do not use that candle for backtesting.
    # ==================================================

    if (
        interval == "5m"
        and not df.empty
    ):
        current_time = (
            pd.Timestamp.now(
                tz="UTC"
            )
        )

        last_timestamp = (
            df.iloc[-1]["timestamp"]
        )

        candle_end = (
            last_timestamp
            + timedelta(minutes=5)
        )

        if current_time < candle_end:
            print(
                "Removing current incomplete "
                "5-minute candle."
            )

            df = (
                df.iloc[:-1]
                .reset_index(drop=True)
            )

    if df.empty:
        raise RuntimeError(
            "No valid candles remain after cleaning."
        )

    # ==================================================
    # CREATE OUTPUT DIRECTORY
    # ==================================================

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ==================================================
    # SAVE CSV
    # ==================================================

    df.to_csv(
        output_path,
        index=False,
    )

    print()
    print("=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)

    print(
        f"Candles  : {len(df):,}"
    )

    print(
        "From     : "
        f"{df.iloc[0]['timestamp']}"
    )

    print(
        "To       : "
        f"{df.iloc[-1]['timestamp']}"
    )

    print(
        f"Saved to : {output_path}"
    )

    print("=" * 60)

    return output_path


def main():
    download_mnq_data()


if __name__ == "__main__":
    main()