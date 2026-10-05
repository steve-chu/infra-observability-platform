
import os
import random
import httpx
import time

from concurrent.futures import ThreadPoolExecutor

#workers for concurrency process
MAX_WORKERS = int(
    os.getenv("MAX_WORKERS", "10")
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000"
)

#time gap for each round metric injection
INTERVAL_SECONDS = float(
    os.getenv("INTERVAL_SECONDS", "5")
)

#assets up to 30
ASSET_LIMIT = int(
    os.getenv("ASSET_LIMIT", "30")
)

#reuse connection to increase efficiency
client = httpx.Client(timeout=5.0)


def get_assets():
    response = client.get(
        f"{API_BASE_URL}/assets"
    )

    response.raise_for_status()

    return response.json()

#inject metric
def send_metric(asset_id, metric_type, metric_value):
    response = client.post(
        f"{API_BASE_URL}/metrics",
        json={
            "asset_id": asset_id,
            "metric_type": metric_type,
            "metric_value": metric_value
        }
    )

    response.raise_for_status()

    return response.json()

#collect all assets data
assets = get_assets()[:ASSET_LIMIT]


#create loop for continuous metric generation
while True:
    round_start = time.perf_counter()
    sent_count = 0
    jobs = []

    #for each asset insert 3 type of metrics and random value
    for asset in assets:
        asset_id = asset["asset_id"]

        metrics = {
            "cpu_usage": round(random.uniform(20, 95), 2),
            "memory_usage": round(random.uniform(30, 90), 2),
            "temperature": round(random.uniform(35, 85), 2),
        }

        for metric_type, metric_value in metrics.items():
            jobs.append(
                (
                    asset_id,
                    metric_type,
                    metric_value
                )
            )
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []

        for asset_id, metric_type, metric_value in jobs:
            future = executor.submit(
                send_metric,
                asset_id,
                metric_type,
                metric_value
            )

            futures.append(future)

        for future in futures:
            future.result()
            sent_count += 1        

            
    #ttl time for each round
    elapsed = time.perf_counter() - round_start
    #metric count per sec
    throughput = sent_count / elapsed

    #display detail result for each round
    print(
        f"Round complete: {sent_count} metric, "
        f"{elapsed:.2f}s, "
        f"{throughput:.2f} metric/sec"
    )

    #metric updata every 5 sec
    time.sleep(INTERVAL_SECONDS)
