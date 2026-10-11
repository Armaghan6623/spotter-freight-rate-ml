"""Pipeline configuration loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class DatasetSpec:
    """One CSV dataset and its Postgres destination."""

    name: str
    table: str
    aliases: tuple[str, ...]
    required: bool = True
    schema: str = "raw"


# Assessment PDF uses underscores; earlier pipeline used hyphens.
DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        name="train_test",
        table="train_test",
        aliases=("train_test.csv", "train-test.csv"),
        required=True,
    ),
    DatasetSpec(
        name="validation",
        table="validation",
        aliases=("validation.csv",),
        required=True,
    ),
    DatasetSpec(
        name="december_chart_inputs",
        table="december_chart_inputs",
        aliases=("december-chart-inputs.csv", "december_chart_inputs.csv"),
        required=True,
    ),
    DatasetSpec(
        name="validation_predictions_template",
        table="validation_predictions_template",
        aliases=(
            "validation_predictions_template.csv",
            "validation-predictions-template.csv",
        ),
        required=True,
    ),
)


def get_database_url() -> str:
    """Return SQLAlchemy DATABASE_URL, building it from POSTGRES_* if needed."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "spotter")
    password = os.getenv("POSTGRES_PASSWORD", "spotter")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "spotter_freight")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
