import os
import time
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv(".env.docker")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")
SQL_DIR = os.path.dirname(os.path.abspath(__file__))

def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_user = os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or "postgres"
    db_password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or "postgres"
    db_host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST") or "localhost"
    db_port = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
    db_name = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB") or "healthcare_db"

    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = get_database_url()


def create_engine_safe(database_url: str):
    try:
        return create_engine(database_url, pool_pre_ping=True)
    except ModuleNotFoundError as exc:
        if getattr(exc, "name", None) == "psycopg2":
            raise RuntimeError(
                "Missing dependency `psycopg2`. Install requirements with `pip install -r requirements.txt`, "
                "or run this via `docker compose up --build`."
            ) from exc
        raise


def wait_for_db(max_retries: int = 20, sleep_seconds: int = 3):
    for attempt in range(max_retries):
        try:
            engine = create_engine_safe(DATABASE_URL)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return engine
        except RuntimeError:
            raise
        except Exception as e:
            print(f"Waiting for database... attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(sleep_seconds)
    raise RuntimeError("Database not available after retries.")


def run_schema(engine) -> None:
    with open(os.path.join(SQL_DIR, "schema.sql"), "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with engine.begin() as conn:
        for stmt in schema_sql.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))


def load_tables(engine) -> None:
    patients = pd.read_csv(os.path.join(CLEAN_DIR, "patients_clean.csv"))
    departments = pd.read_csv(os.path.join(CLEAN_DIR, "departments_clean.csv"))
    visits = pd.read_csv(os.path.join(CLEAN_DIR, "visits_clean.csv"))

    patients.to_sql("dim_patient", engine, if_exists="append", index=False)
    departments.to_sql("dim_department", engine, if_exists="append", index=False)
    visits.to_sql("fact_visits", engine, if_exists="append", index=False)

    print("Data loaded successfully.")


def main() -> None:
    engine = wait_for_db()
    run_schema(engine)
    load_tables(engine)


if __name__ == "__main__":
    main()
