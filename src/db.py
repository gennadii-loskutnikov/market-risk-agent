import sqlite3
import os
from pathlib import Path
from src.config import DATABASE_PATH


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path) as f:
        schema = f.read()
    with get_conn() as conn:
        conn.executescript(schema)
