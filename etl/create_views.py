import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv(".env.docker")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def main() -> None:
    engine = create_engine_safe(DATABASE_URL)

    with open(os.path.join(SQL_DIR, "views.sql"), "r", encoding="utf-8") as f:
        view_sql = f.read()

    with engine.begin() as conn:
        for stmt in view_sql.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))

    print("Views created successfully.")


if __name__ == "__main__":
    main()
