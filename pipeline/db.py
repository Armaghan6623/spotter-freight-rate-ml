"""PostgreSQL connection helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from pipeline.config import SQL_DIR, get_database_url


def create_db_engine(echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for Postgres."""
    return create_engine(get_database_url(), echo=echo, pool_pre_ping=True)


def check_connection(engine: Engine) -> None:
    """Raise if Postgres is unreachable."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _split_sql_statements(sql: str) -> list[str]:
    """Split a SQL script into executable statements (skip comment-only chunks)."""
    statements: list[str] = []
    for chunk in sql.split(";"):
        lines = [
            line
            for line in chunk.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        statement = "\n".join(lines).strip()
        if statement:
            statements.append(statement)
    return statements


def apply_schema(engine: Engine, schema_path: Path | None = None) -> None:
    """Apply sql/schema.sql (safe to re-run; uses IF NOT EXISTS)."""
    path = schema_path or (SQL_DIR / "schema.sql")
    sql = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in _split_sql_statements(sql):
            conn.execute(text(statement))


def table_row_count(engine: Engine, schema: str, table: str) -> int:
    """Return number of rows in schema.table."""
    with engine.connect() as conn:
        result = conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table}"'))
        return int(result.scalar_one())
