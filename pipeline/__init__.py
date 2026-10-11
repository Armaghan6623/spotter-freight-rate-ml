"""Spotter freight-rate data pipeline package."""

__all__ = ["ingest_all"]


def __getattr__(name: str):
    if name == "ingest_all":
        from pipeline.ingest import ingest_all

        return ingest_all
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
