"""
Complete CSV → PostgreSQL ingestion script.

Convert Notebook to Script
--------------------------
This module replaces ad-hoc notebook cells with a reproducible script:
  1. Resolve CSV files under data/
  2. Load + light clean with pandas
  3. Validate shape / nulls / duplicates
  4. Truncate + reload into raw.* tables
  5. Log each run in raw.ingestion_runs

Running the Script
------------------
  # start Postgres
  docker compose up -d

  # install deps (once)
  uv sync

  # ingest everything
  python -m pipeline.ingest

  # or via the full pipeline orchestrator
  python -m pipeline.pipeline
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import Date, Float, Text, text
from sqlalchemy.engine import Engine

from pipeline.config import DATA_DIR, DATASETS, DatasetSpec
from pipeline.db import apply_schema, check_connection, create_db_engine, table_row_count


# ---------------------------------------------------------
# Path helpers
# ---------------------------------------------------------

def ensure_data_directory() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def resolve_csv_path(spec: DatasetSpec) -> Path:
    """Find the first existing alias for a dataset under data/."""
    data_dir = ensure_data_directory()
    for alias in spec.aliases:
        candidate = data_dir / alias
        if candidate.exists():
            return candidate
    tried = ", ".join(spec.aliases)
    raise FileNotFoundError(
        f"Missing dataset '{spec.name}'. Place one of [{tried}] in {data_dir}"
    )


# ---------------------------------------------------------
# Load + clean (notebook-style cells → functions)
# ---------------------------------------------------------

def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Data file is empty: {path}")
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize columns and parse dates for warehouse load."""
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]

    # Clean text columns first (exclude date so we do not stringify it)
    text_cols = [
        c
        for c in out.columns
        if c != "date" and (
            pd.api.types.is_object_dtype(out[c])
            or pd.api.types.is_string_dtype(out[c])
        )
    ]
    for col in text_cols:
        out[col] = out[col].astype("string").str.strip()
        out[col] = out[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    # Keep as datetime64 so SQLAlchemy binds DATE correctly (not VARCHAR)
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")

    return out


def validate_dataframe(df: pd.DataFrame, name: str) -> dict:
    """Basic validation checks; prints a report and returns summary stats."""
    duplicate_count = int(df.duplicated().sum())
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)

    print(f"\n{'=' * 60}")
    print(f"VALIDATION: {name}")
    print(f"{'=' * 60}")
    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")
    print(f"Duplicate rows: {duplicate_count}")

    if missing.empty:
        print("Missing values: None")
    else:
        print("\nMissing values:")
        print(missing)

    print("\nData types:")
    print(df.dtypes)
    print("\nColumns:")
    print(list(df.columns))

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "duplicates": duplicate_count,
        "missing_columns": missing.to_dict() if not missing.empty else {},
    }


def inspect_dataframe(df: pd.DataFrame, name: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"INSPECTION: {name}")
    print(f"{'=' * 60}")
    print("\nFirst 5 rows:")
    print(df.head())
    print("\nLast 5 rows:")
    print(df.tail())
    print("\nStatistical summary:")
    print(df.describe(include="all").transpose())


# ---------------------------------------------------------
# Postgres write
# ---------------------------------------------------------

# Columns we keep for each table when present in the CSV
TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "train_test": (
        "load_id",
        "pickup",
        "delivery",
        "pickup_lat",
        "pickup_lon",
        "delivery_lat",
        "delivery_lon",
        "distance",
        "equipment",
        "weight",
        "date",
        "market_index",
        "quote_signal",
        "rate",
    ),
    "validation": (
        "load_id",
        "pickup",
        "delivery",
        "pickup_lat",
        "pickup_lon",
        "delivery_lat",
        "delivery_lon",
        "distance",
        "equipment",
        "weight",
        "date",
        "market_index",
        "quote_signal",
    ),
    "december_chart_inputs": (
        "pickup",
        "delivery",
        "distance",
        "equipment",
        "weight",
        "date",
        "predicted_rate",
    ),
    "validation_predictions_template": (
        "load_id",
        "predicted_rate",
    ),
}


def align_columns(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """
    Keep known warehouse columns; allow train target aliases.

    Train CSVs sometimes name the label `rate`, `actual_rate`, or `freight_rate`.
    """
    out = df.copy()

    if table == "train_test" and "rate" not in out.columns:
        for alias in ("actual_rate", "freight_rate", "target", "y"):
            if alias in out.columns:
                out = out.rename(columns={alias: "rate"})
                break

    wanted = TABLE_COLUMNS[table]
    present = [c for c in wanted if c in out.columns]
    missing_required = [c for c in wanted if c not in out.columns]

    # rate may be absent until the labeled file is inspected — warn, don't crash
    if table == "train_test":
        missing_required = [c for c in missing_required if c != "rate"]

    if missing_required:
        print(
            f"  Warning: {table} CSV missing expected columns: {missing_required}. "
            "Ingesting available columns only."
        )

    aligned = out[present].copy()
    for col in wanted:
        if col not in aligned.columns:
            aligned[col] = pd.NA
    return aligned[list(wanted)]


def log_ingestion_run(
    engine: Engine,
    dataset_name: str,
    source_file: str,
    row_count: int,
    status: str,
    message: str,
    started_at: datetime,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO raw.ingestion_runs
                    (dataset_name, source_file, row_count, status, message, started_at, finished_at)
                VALUES
                    (:dataset_name, :source_file, :row_count, :status, :message, :started_at, :finished_at)
                """
            ),
            {
                "dataset_name": dataset_name,
                "source_file": source_file,
                "row_count": row_count,
                "status": status,
                "message": message,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc),
            },
        )


def ingest_dataframe(
    engine: Engine,
    df: pd.DataFrame,
    spec: DatasetSpec,
    source_file: str,
) -> int:
    """Replace table contents with the cleaned DataFrame."""
    started = datetime.now(timezone.utc)
    aligned = align_columns(df, spec.table)
    full_table = f"{spec.schema}.{spec.table}"

    try:
        with engine.begin() as conn:
            conn.execute(text(f'TRUNCATE TABLE "{spec.schema}"."{spec.table}" RESTART IDENTITY'))

        dtype = {}
        for col in aligned.columns:
            if col == "date":
                dtype[col] = Date()
            elif aligned[col].dtype == object or str(aligned[col].dtype) == "string":
                dtype[col] = Text()
            elif pd.api.types.is_float_dtype(aligned[col]):
                dtype[col] = Float()

        aligned.to_sql(
            name=spec.table,
            con=engine,
            schema=spec.schema,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
            dtype=dtype,
        )
        count = table_row_count(engine, spec.schema, spec.table)
        log_ingestion_run(
            engine,
            spec.name,
            source_file,
            count,
            "success",
            f"Loaded into {full_table}",
            started,
        )
        print(f"  Ingested {count:,} rows -> {full_table}")
        return count
    except Exception as exc:  # noqa: BLE001 - surface + log, then re-raise
        log_ingestion_run(
            engine,
            spec.name,
            source_file,
            0,
            "failed",
            str(exc),
            started,
        )
        raise


# ---------------------------------------------------------
# Orchestration
# ---------------------------------------------------------

def ingest_all(
    engine: Engine | None = None,
    *,
    skip_missing: bool = False,
    inspect_train: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Full ingestion: CSV → validate → Postgres.

    Returns the loaded DataFrames for downstream ML stages.
    """
    own_engine = engine is None
    engine = engine or create_db_engine()

    print("\n" + "=" * 60)
    print("SPOTTER DATA INGESTION -> POSTGRESQL")
    print("=" * 60)

    print("\nChecking Postgres connection...")
    check_connection(engine)
    print("Postgres is reachable.")

    print("\nApplying schema (IF NOT EXISTS)...")
    apply_schema(engine)
    print("Schema ready.")

    loaded: dict[str, pd.DataFrame] = {}

    for spec in DATASETS:
        print(f"\n--- Dataset: {spec.name} ---")
        try:
            path = resolve_csv_path(spec)
        except FileNotFoundError as exc:
            if skip_missing or not spec.required:
                print(f"  Skipped (missing): {exc}")
                continue
            raise

        print(f"  Source: {path.name}")
        df = clean_dataframe(load_csv(path))
        validate_dataframe(df, spec.name)

        if inspect_train and spec.name == "train_test":
            inspect_dataframe(df, "Training / Development Data")

        ingest_dataframe(engine, df, spec, path.name)
        loaded[spec.name] = df

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    for spec in DATASETS:
        if spec.name not in loaded:
            continue
        rows = table_row_count(engine, spec.schema, spec.table)
        print(f"  {spec.schema}.{spec.table}: {rows:,} rows")

    if own_engine:
        engine.dispose()

    return loaded


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Spotter freight CSVs into PostgreSQL."
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip datasets whose CSV is not present (useful before train_test.csv is added).",
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
        ingest_all(skip_missing=args.skip_missing, inspect_train=not args.no_inspect)
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print(
            "\nTip: copy assessment CSVs into data/, or re-run with --skip-missing "
            "to ingest whatever is available.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
