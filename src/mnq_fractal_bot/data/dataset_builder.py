"""
Multi-Timeframe 2-Year Dataset Builder for MNQ Futures
Downloads:
1. 2 Years of 1-Hour Institutional Candles (13,735 candles from May 2024 to present)
2. 2 Years of Daily Candles (504 trading days)
3. Full 60-day Intraday 5-minute Candles (13,669 candles)
"""
import logging
from pathlib import Path
import yfinance as yf
import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("DatasetBuilder")

def build_datasets(output_dir: str = "data"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    ticker = yf.Ticker("MNQ=F")
    
    # 1. 2-Year 1-Hour Dataset
    logger.info("Downloading 2-Year 1-Hour candles for MNQ=F...")
    df_1h = ticker.history(period="730d", interval="1h")
    if not df_1h.empty:
        csv_1h = out_path / "mnq_1h_2years.csv"
        df_1h.reset_index(inplace=True)
        # Rename columns standard format
        df_1h.rename(columns={"Datetime": "timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
        df_1h.to_csv(csv_1h, index=False)
        logger.info(f"Saved {len(df_1h)} 1-hour candles to {csv_1h}")

    # 2. 2-Year Daily Dataset
    logger.info("Downloading 2-Year Daily candles for MNQ=F...")
    df_1d = ticker.history(period="2y", interval="1d")
    if not df_1d.empty:
        csv_1d = out_path / "mnq_1d_2years.csv"
        df_1d.reset_index(inplace=True)
        df_1d.rename(columns={"Date": "timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
        df_1d.to_csv(csv_1d, index=False)
        logger.info(f"Saved {len(df_1d)} daily candles to {csv_1d}")

    # 3. 60-Day 5-Minute Dataset
    logger.info("Downloading full 60-day 5-minute candles for MNQ=F...")
    df_5m = ticker.history(period="60d", interval="5m")
    if not df_5m.empty:
        csv_5m = out_path / "mnq_5m_deep.csv"
        df_5m.reset_index(inplace=True)
        df_5m.rename(columns={"Datetime": "timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
        df_5m.to_csv(csv_5m, index=False)
        logger.info(f"Saved {len(df_5m)} 5-minute candles to {csv_5m}")

if __name__ == "__main__":
    build_datasets()
