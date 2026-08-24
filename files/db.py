"""Connexion à la base SQLite du module d'entraînement mental."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "mental_training.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec les lignes accessibles par nom de colonne."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path = DB_PATH, reset: bool = False) -> sqlite3.Connection:
    """Crée (ou recrée) les tables à partir du schéma."""
    if reset and db_path.exists():
        db_path.unlink()

    conn = get_connection(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    return conn
