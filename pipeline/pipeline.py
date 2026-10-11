"""
Full Spotter data pipeline orchestrator.

Stages
------
1. Ensure data/ exists and CSVs are present
2. Connect to PostgreSQL and apply schema
3. Ingest CSVs into raw.* tables (complete ingestion script)
4. Hand DataFrames back for the next stage: feature engineering + ML

Usage
-----
  docker compose up -d
  uv sync
  python -m pipeline.pipeline
  python -m pipeline.pipeline --skip-missing   # if train_test.csv not yet added
"""

from __future__ import annotations

import argparse
import sys

from pipeline.ingest import ingest_all


def run_pipeline(*, skip_missing: bool = False, inspect_train: bool = True):
    """
    Execute the data pipeline end-to-end.

    Returns a dict of DataFrames keyed by dataset name, ready for ML work.
    """
    print("\n" + "=" * 60)
    print("SPOTTER FREIGHT RATE ML - DATA PIPELINE")
    print("=" * 60)

    datasets = ingest_all(
        skip_missing=skip_missing,
        inspect_train=inspect_train,
    )

    print("\nNext stage (not yet implemented): feature engineering + model training.")
    print("You can read warehouse tables with pandas.read_sql / SQLAlchemy.")
    return datasets


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Spotter data pipeline.")
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip datasets whose CSV is not present.",
    )
    parser.add_argument(
        "--no-inspect",
        action="store_true",
        help="Skip printing train head/tail/describe.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_pipeline(
            skip_missing=args.skip_missing,
            inspect_train=not args.no_inspect,
        )
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print(
            "\nPlace train_test.csv in data/ (assessment name) "
            "or pass --skip-missing to ingest the other CSVs now.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # Keep a single CLI surface; ingest_main is available via `python -m pipeline.ingest`
    raise SystemExit(main())
