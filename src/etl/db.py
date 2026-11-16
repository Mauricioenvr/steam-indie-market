"""Conexión a PostgreSQL a partir de las variables del archivo .env."""
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def connect() -> psycopg.Connection:
    """Abre una conexión usando PGHOST, PGPORT, PGDATABASE, PGUSER y PGPASSWORD."""
    return psycopg.connect()  # psycopg lee las variables PG* del entorno


def run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    """Ejecuta un archivo .sql completo."""
    conn.execute(path.read_text(encoding="utf-8"))
    conn.commit()
