# Healthcare Analytics (ETL + Postgres + Streamlit)

This application generates synthetic healthcare visit data, stores it in PostgreSQL, builds an analytics layer with SQL views, and presents insights through an interactive Streamlit dashboard.

## Demo

![Healthcare Analytics demo](Health_demo.gif)

## What’s inside

- `etl/` — data generation, cleaning, database load, and view creation
- `etl/schema.sql` — tables (`dim_patient`, `dim_department`, `fact_visits`)
- `etl/views.sql` — analytics views used by the dashboard
- `dashboard/app.py` — Streamlit app (filters, KPIs, charts, exports)
- `docker-compose.yml` — Postgres + ETL + dashboard services
- `dockerfile` — Python image used by ETL + dashboard

## Quick start (Docker Compose)

Prereqs:
- Docker Desktop (or Docker Engine) with `docker compose`

Run everything:

```bash
docker compose up --build
```

Then open:
- Dashboard: `http://localhost:8501`

Useful commands:

```bash
# Re-run the ETL pipeline (generate → transform → load → views)
docker compose run --rm etl

# Stop containers
docker compose down

# Full reset (drops the Postgres volume)
docker compose down -v
```

## Local run (without Docker)

You can run the dashboard locally if you already have a Postgres instance available.

1) Create a virtualenv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Set environment variables (or edit `.env`):

For local runs, `DB_HOST` should typically be `localhost`. This repo’s `.env` is set up for local runs by default.

Docker Compose uses `.env.docker` (which sets `DATABASE_URL=postgresql://...@postgres:5432/...`, resolvable only inside the Compose network).

Optional: create a `.env.local` for per-machine local overrides:

```bash
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=healthcare_db
```


3) Run the pipeline:

```bash
python3 etl/generate_data.py
python3 etl/transform.py
python3 etl/load.py
python3 etl/create_views.py
```

4) Start the app:

```bash
streamlit run dashboard/app.py
```

## Data notes

- The ETL creates synthetic data using Faker and saves intermediate CSVs under `data/` (created at runtime).
- The dashboard reads from Postgres (it queries the visit-level tables and slices them based on the sidebar filters).
