from pathlib import Path

from mnq_fractal_bot.execution.paper_stream_cli import parse_args, run_paper_stream


def test_parse_args_defaults():
    args = parse_args(["data/sample_mnq_5m.csv"])
    assert args.csv_path == Path("data/sample_mnq_5m.csv")
    assert args.warmup_candles == 500
    assert args.delay == 0.0
    assert args.max_stop_points == 50.0
    assert args.c3_only is True
    assert args.initial_balance == 25000.0


def test_parse_args_custom():
    args = parse_args([
        "data/sample_mnq_5m.csv",
        "--warmup-candles", "100",
        "--delay", "0.01",
        "--max-stop-points", "40.0",
        "--initial-balance", "50000.0",
    ])
    assert args.warmup_candles == 100
    assert args.delay == 0.01
    assert args.max_stop_points == 40.0
    assert args.initial_balance == 50000.0


def test_run_paper_stream_sample_file(capsys):
    args = parse_args(["data/sample_mnq_5m.csv", "--warmup-candles", "0"])
    exit_code = run_paper_stream(args)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "MNQ FRACTAL BOT — FORWARD PAPER STREAM RUNNER" in captured.out
    assert "FORWARD PAPER STREAM COMPLETE" in captured.out


def test_run_paper_stream_missing_file():
    args = parse_args(["nonexistent.csv"])
    exit_code = run_paper_stream(args)
    assert exit_code == 1
