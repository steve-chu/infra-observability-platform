import time

from app.db import get_connection

ITERATIONS = 50

start = time.perf_counter()

for _ in range(ITERATIONS):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()

elapsed = time.perf_counter() - start

print(
    f"New connection each time: "
    f"{ITERATIONS} queries in {elapsed:.2f}s"
)

start = time.perf_counter()

with get_connection() as conn:
    for _ in range(ITERATIONS):
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()

elapsed = time.perf_counter() - start

print(
    f"Reused connection: "
    f"{ITERATIONS} queries in {elapsed:.2f}s"
)