# spotter-freight-rate-ml

Freight-rate ML assessment pipeline: load assessment CSVs, validate them, and ingest into **PostgreSQL**. Modeling comes next on top of the warehouse tables.

## Layout

```
data/                      # place assessment CSVs here (gitignored)
pipeline/
  config.py                # paths + dataset aliases
  db.py                    # Postgres engine / schema apply
  ingest.py                # complete CSV → Postgres ingestion script
  pipeline.py              # full orchestrator
sql/schema.sql             # raw + ml schemas
docker-compose.yml         # local Postgres 16
.env.example               # copy to .env
```

## Prerequisites

- Docker Desktop (for Postgres)
- [uv](https://github.com/astral-sh/uv) (or pip)
- Python 3.14+ (see `.python-version`)

## 1. Place data files

Copy assessment files into `data/` (either naming style works):

| Role | Accepted filenames |
|------|--------------------|
| Labeled train/dev | `train_test.csv` or `train-test.csv` |
| Validation loads | `validation.csv` |
| December chart | `december-chart-inputs.csv` |
| Predictions template | `validation_predictions_template.csv` or `validation-predictions-template.csv` |

## 2. Start PostgreSQL

```bash
cp .env.example .env          # Windows: copy .env.example .env
docker compose up -d
docker compose ps             # wait until healthy
```

Default connection (also in `.env`):

```text
postgresql+psycopg://spotter:spotter@localhost:5433/spotter_freight
```

If you already have Postgres in a Codespace / remote host, set `DATABASE_URL` in `.env` to that instance instead of using Docker.

## 3. Install dependencies

```bash
uv sync
```

## 4. Run ingestion

**Complete ingestion script** (CSV → validate → `raw.*` tables):

```bash
uv run python -m pipeline.ingest
```

If `train_test.csv` is not in `data/` yet, ingest the rest first:

```bash
uv run python -m pipeline.ingest --skip-missing
```

**Full pipeline orchestrator** (same ingestion today; ML stages later):

```bash
uv run python -m pipeline.pipeline
# or
uv run python -m pipeline.pipeline --skip-missing
```

## 5. Verify rows in Postgres

```bash
docker compose exec postgres psql -U spotter -d spotter_freight -c "\dt raw.*"
docker compose exec postgres psql -U spotter -d spotter_freight -c "SELECT COUNT(*) FROM raw.validation;"
docker compose exec postgres psql -U spotter -d spotter_freight -c "SELECT * FROM raw.ingestion_runs ORDER BY id DESC LIMIT 10;"
```

## Warehouse tables

| Table | Purpose |
|-------|---------|
| `raw.train_test` | Labeled development data |
| `raw.validation` | 12,000 loads to score |
| `raw.december_chart_inputs` | December chart lanes |
| `raw.validation_predictions_template` | Submission template |
| `raw.ingestion_runs` | Audit log of each load |
| `ml.validation_predictions` | Model outputs (next stage) |

## Codespace note

If Postgres is already running in GitHub Codespaces, skip `docker compose` and point `.env` at that service (`POSTGRES_HOST` / `DATABASE_URL`). Then run `uv run python -m pipeline.ingest` from the repo root.

## Next step

Feature engineering + model training reading from `raw.train_test` / `raw.validation`, writing predictions to `ml.validation_predictions` and `validation_predictions.csv`.
