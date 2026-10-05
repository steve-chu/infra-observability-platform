import os
import psycopg
from psycopg.rows import dict_row

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "observability"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "2")),
        row_factory=dict_row
    )
