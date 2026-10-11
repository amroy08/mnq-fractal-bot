import argparse
import sys
from pathlib import Path

from mnq_fractal_bot.execution.paper_stream_cli import parse_args, run_paper_stream


def main() -> None:
    """
    Main entrypoint for MNQ Fractal Bot.
    Runs local forward paper trading stream by default.
    """
    if len(sys.argv) == 1:
        # Default behavior: run paper stream on standard dataset
        default_csv = Path("data/mnq_5m_real.csv")
        if default_csv.exists():
            args = parse_args([str(default_csv), "--warmup-candles", "500"])
            sys.exit(run_paper_stream(args))
        else:
            sample_csv = Path("data/sample_mnq_5m.csv")
            args = parse_args([str(sample_csv), "--warmup-candles", "0"])
            sys.exit(run_paper_stream(args))

    sys.exit(run_paper_stream(parse_args()))


if __name__ == "__main__":
    main()