"""
db.py
─────
PostgreSQL connection helper.
Connects to Azure Database for PostgreSQL using psycopg2.

Required env vars:
    AZURE_PG_HOST      — e.g. your-server.postgres.database.azure.com
    AZURE_PG_PORT      — default 5432
    AZURE_PG_DATABASE  — e.g. claims_db
    AZURE_PG_USER      — e.g. adminuser@your-server
    AZURE_PG_PASSWORD  — password
    AZURE_PG_SSLMODE   — default "require"
"""

import logging
import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

log = logging.getLogger(__name__)

PG_HOST = os.getenv("AZURE_PG_HOST", "localhost")
PG_PORT = int(os.getenv("AZURE_PG_PORT", "5432"))
PG_DATABASE = os.getenv("AZURE_PG_DATABASE", "claims_db")
PG_USER = os.getenv("AZURE_PG_USER", "postgres")
PG_PASSWORD = os.getenv("AZURE_PG_PASSWORD", "")
PG_SSLMODE = os.getenv("AZURE_PG_SSLMODE", "require")


def get_db_connection():
    """Returns a psycopg2 connection to Azure PostgreSQL with RealDictCursor."""
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
        sslmode=PG_SSLMODE,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False
    return conn


def row_to_dict(row):
    """Converts a psycopg2 RealDictRow (or list of rows) into plain dict(s)."""
    if row is None:
        return None
    if isinstance(row, list):
        return [dict(r) for r in row]
    return dict(row)
