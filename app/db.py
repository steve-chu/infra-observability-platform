import os
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


#build connection pool, reduce time for building conn between api <-> db
pool = ConnectionPool(
    conninfo=(
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'observability')} "
        f"user={os.getenv('DB_USER', 'postgres')} "
        f"password={os.getenv('DB_PASSWORD', 'postgres')} "
        f"connect_timeout={os.getenv('DB_CONNECT_TIMEOUT', '2')}"
    ),
    kwargs={
        "row_factory": dict_row
    },
    min_size=2,
    max_size=10,
    timeout=2,
    open=True
)

def get_connection():
    return pool.connection()

