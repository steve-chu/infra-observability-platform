# Distributed Infrastructure Observability & Incident Management Platform

一個以 Backend / SRE 為核心的基礎設施可觀測性與事件管理平台。

此專案用來模擬較接近實際工程環境的 Backend + SRE 工作流程，涵蓋：

- Infrastructure asset management
- Telemetry ingestion
- Incident management
- Database connection pooling
- Load testing
- Performance investigation
- Prometheus monitoring
- Grafana dashboard
- Failure simulation
- Alerting
- Recovery testing
- Automated testing
- GitHub Actions CI

V1 的重點是實際觀察系統在負載、資料庫故障與恢復情境下的行為。

---

## Architecture

```text
                         ┌─────────────────┐
                         │     Client      │
                         └────────┬────────┘
                                  │ HTTP
                                  ▼
                         ┌─────────────────┐
                         │     FastAPI     │
                         │    infra-api    │
                         └────────┬────────┘
                                  │
                         psycopg connection pool
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  PostgreSQL 17  │
                         │ infra-postgres  │
                         └─────────────────┘


FastAPI
   │
   │ /prometheus
   ▼
┌─────────────────┐
│   Prometheus    │
│ infra-prometheus│
└────────┬────────┘
         │ PromQL
         ▼
┌─────────────────┐
│     Grafana     │
│  infra-grafana  │
└─────────────────┘
```

目前所有服務皆透過 Docker Compose 執行。

Grafana datasource 與 dashboard 設定也已放入 repository 並使用 provisioning，因此可以從乾淨環境重新建立 monitoring dashboard，而不依賴本機既有的 Grafana volume。

---

## Domain Model

Backend 主要資料關係如下：

```text
Site
 └── Asset
      ├── Metric
      └── Incident
```

### Site

代表不同廠區或基礎設施位置。

### Asset

代表各 Site 中管理的設備或系統資源。

### Metric

記錄 Asset 的 telemetry 資料，例如：

```text
cpu_usage
memory_usage
temperature
```

### Incident

記錄設備或系統發生的異常事件，以及事件處理狀態。

---

## API Endpoints

### Health

```text
GET /health
GET /ready
```

`/health` 用來確認 FastAPI process 是否仍正常存活。

`/ready` 除了確認 API process，也會實際檢查 PostgreSQL 是否可連線，用來判斷服務目前是否適合接收流量。

---

### Sites

```text
GET  /sites
POST /sites
GET  /sites/{site_id}
```

---

### Assets

```text
GET   /assets
POST  /assets
GET   /assets/{asset_id}
PATCH /assets/{asset_id}/status
```

支援 Asset status：

```text
healthy
degraded
unhealthy
maintenance
```

---

### Metrics

```text
GET  /metrics
POST /metrics
```

Metric query 支援 Asset、Metric Type 與時間範圍等條件查詢。

---

### Incidents

```text
GET   /incidents
POST  /incidents
PATCH /incidents/{incident_id}/status
```

---

## Incident Lifecycle

Incident 狀態依照以下流程轉換：

```text
open
  ↓
investigating
  ↓
resolved
  ↓
closed
```

如果要求不合法的狀態轉換，API 會回傳：

```text
409 Conflict
```

此流程也有透過 pytest 驗證。

---

## Backend & Database

目前 Backend Stack：

- Python 3.12
- FastAPI
- PostgreSQL 17
- psycopg
- psycopg-pool
- Pydantic
- Raw SQL

使用SQL 與 transaction flow 直接透過 psycopg 處理。

Database connection 使用 connection pool，而不是每次 HTTP request 都重新建立 PostgreSQL connection。

目前 pool 主要設定：

```text
min_size = 2
max_size = 10
pool acquisition timeout = 2 seconds
```

---

## Telemetry Generator

專案包含 telemetry generator，用來模擬多個 Asset 持續送入監控資料。

目前模擬的 metric type：

```text
cpu_usage
memory_usage
temperature
```

Generator 使用 `ThreadPoolExecutor` 建立 concurrent HTTP requests，並可以透過環境變數調整 concurrency。

例如：

```powershell
$env:MAX_WORKERS="20"
python scripts/telemetry_generator.py
```

這讓 Backend 可以在持續 ingestion 的情況下進行 throughput 與 latency 測試，而不只是在單一 request 情境下驗證 API。

---

## Database Connection Benchmark

專案中另外建立了一個 database connection benchmark，用來比較：

```text
每次 query 建立新 connection
vs
重複使用既有 connection
```

本機測試結果約為：

```text
New connection + SELECT 1
~32 ms / operation

Reused connection + SELECT 1
~1.6 ms / operation
```

這個結果顯示 PostgreSQL connection setup 本身具有明顯成本。

因此 Backend 後續加入 `psycopg_pool.ConnectionPool`。

---

## Connection Pool Performance

在 telemetry ingestion workload 下進行 concurrent testing。

### Connection Pool 前

```text
10 workers   ~120 metrics/sec
20 workers   ~125 metrics/sec
40 workers   ~74 metrics/sec
```

### Connection Pool 後

```text
10 workers   ~150 metrics/sec
20 workers   ~174 metrics/sec
40 workers   ~146 metrics/sec
```

可以看到 connection pooling 對 concurrent ingestion throughput 有明顯改善。

另外也測試：

```text
pool max_size = 10
vs
pool max_size = 20
```

結果顯示將 pool size 增加到 20 並沒有提升 throughput。

這表示：

> 更多 database connections 不一定代表更高效能，pool size 仍需要依照實際 workload 與 bottleneck 調整。

以上 benchmark 為本機特定測試環境結果，主要用途是 bottleneck investigation，而不是 production benchmark。

---

## Performance Investigation

在 connection pooling 完成後，也進一步觀察 request latency。

測試期間觀察到：

```text
connection pool wait
SQL execution
transaction commit
```

其中 PostgreSQL transaction / WAL sync 會佔用部分 request latency。

測試期間也透過 PostgreSQL `pg_stat_activity` 觀察 connection state 與 wait event。

最後確認：

- 沒有 long-running transaction leak
- Connection pool capacity 並非主要剩餘 bottleneck
- 單純增加 pool size 無法持續提升效能

因此 V1 沒有繼續無限制增加 database connections。

---

## Observability

FastAPI 暴露 Prometheus metrics endpoint：

```text
GET /prometheus
```

目前主要自訂 metrics：

```text
http_requests_total
http_request_duration_seconds
telemetry_ingested_total
```

此外 `prometheus-client` 也會自動提供 Python process runtime metrics。

---

## HTTP Metrics

HTTP middleware 會記錄：

```text
HTTP method
route
status code
request duration
```

例如：

```text
method="POST"
endpoint="/metrics"
status="201"
```

Metric label 使用 route template：

```text
/assets/{asset_id}
```

而不是：

```text
/assets/1
/assets/2
/assets/3
```

這可以避免每個不同 ID 都產生新的 Prometheus label，降低 high-cardinality metric 問題。

---

## Prometheus

Prometheus 透過 Docker Compose 執行。

Prometheus scrape target：

```text
http://api:8000/prometheus
```

Scrape interval：

```text
15 seconds
```

資料流：

```text
FastAPI
   ↓
/prometheus
   ↓
Prometheus scrape
   ↓
Prometheus TSDB
   ↓
PromQL
   ↓
Grafana
```

---

## PromQL Examples

### Total API Request Rate

```promql
sum(rate(http_requests_total[1m]))
```

---

### Telemetry Ingestion Rate

```promql
rate(telemetry_ingested_total[1m])
```

---

### POST /metrics p95 Latency

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(
      http_request_duration_seconds_bucket{
        endpoint="/metrics",
        method="POST"
      }[1m]
    )
  )
)
```

---

### HTTP 5xx Error Rate

```promql
(
  sum(
    rate(
      http_requests_total{status=~"5.."}[1m]
    )
  ) or vector(0)
)
/
clamp_min(
  (
    sum(
      rate(http_requests_total[1m])
    ) or vector(0)
  ),
  0.000001
)
* 100
```

---

## Grafana Dashboard

目前 Grafana Dashboard 主要依照 API 的 RED 類型訊號設計：

```text
Rate
Errors
Duration
```

另外加入 telemetry ingestion throughput。

Dashboard 目前包含四個主要 Panel：

```text
Total API RPS
Telemetry Ingestion Rate
POST /metrics p95 Latency
HTTP 5xx Error Rate
```

Grafana 在 Docker network 內透過：

```text
http://prometheus:9090
```

查詢 Prometheus。

---

## Grafana Provisioning

Prometheus datasource 與 dashboard 都已經以 provisioning file 管理。

Repository 中包含：

```text
monitoring/
└── grafana/
    ├── dashboards/
    │   └── api-observability-dashboard.json
    │
    └── provisioning/
        ├── dashboards/
        │   └── dashboard.yml
        │
        └── datasources/
            └── prometheus.yml
```

曾使用一個全新的 Grafana container 進行 clean-room test。

該 container：

```text
沒有既有 grafana_data
沒有手動設定 datasource
沒有手動建立 dashboard
```

啟動後可以自動：

```text
建立 Prometheus datasource
↓
載入 API Observability Dashboard
↓
執行 PromQL
↓
顯示 FastAPI RPS
```

因此 Grafana monitoring environment 可以從 repository 重建。

---

## Failure Simulation

V1 進行過 PostgreSQL outage simulation。

測試方式：

```text
停止 PostgreSQL container
但保持 FastAPI / Prometheus / Grafana 運作
```

觀察結果：

```text
PostgreSQL DOWN
        ↓
FastAPI process 仍正常
        ↓
/health → 200
/ready  → 503
        ↓
HTTP 5xx metrics 增加
        ↓
Prometheus 收到 failure metrics
        ↓
Grafana Alert Firing
```

這也驗證了：

```text
Liveness
vs
Readiness
```

兩者的差異。

---

## Liveness vs Readiness

### `/health`

確認：

```text
Application process 是否還活著
```

即使 PostgreSQL 掛掉：

```text
/health → 200
```

仍然合理，因為 FastAPI process 本身還正常。

---

### `/ready`

確認：

```text
Application 是否具備提供正常服務的能力
```

PostgreSQL unavailable 時：

```text
/ready → 503
```

表示目前不應將正常 production traffic 導入此 instance。

---

## Readiness Timeout Investigation

第一次執行 database outage test 時發現：

```text
GET /ready
→ 約 30 秒後才回 503
```

進一步 investigation 後確認：

```text
DB connection timeout
```

與：

```text
Connection pool acquisition timeout
```

是不同的 timeout。

### `connect_timeout`

控制：

```text
建立 PostgreSQL connection 時最多等待多久
```

### Pool `timeout`

控制：

```text
Application 從 connection pool 等待可用 connection 最多多久
```

原本 connection pool 使用預設等待時間，因此 outage 時 `/ready` 可能卡住約 30 秒。

後續加入：

```text
pool timeout = 2 seconds
```

使 readiness check 可以快速失敗。

實際測試中，在 pool 已經辨識 PostgreSQL unavailable 後：

```text
/ready → 503
```

可以在數十毫秒內返回，而不是阻塞 30 秒。

---

## Recovery Testing

PostgreSQL 恢復後，另外測試 connection pool 是否可以自行恢復。

流程：

```text
PostgreSQL START
        ↓
Container healthy
        ↓
Docker DNS resolves "postgres"
        ↓
API container 可直接連 PostgreSQL
        ↓
Connection pool background reconnect
        ↓
/ready → 200
```

Connection pool 最後可以自行補回可用 connection，不需要重新啟動 FastAPI container。

完整 failure lifecycle：

```text
Normal
  ↓
Database failure
  ↓
Pending
  ↓
Firing
  ↓
Database recovery
  ↓
Normal
```

---

## Grafana Alerting

目前建立：

```text
High HTTP 5xx Error Rate
```

Alert condition：

```text
HTTP 5xx Error Rate > 5%
```

設定：

```text
Evaluation interval = 1 minute
Pending period = 1 minute
```

實際 failure simulation 中成功觀察：

```text
Normal
↓
Pending
↓
Firing
↓
Normal
```

證明從 application failure 到 monitoring alert 的完整資料鏈可以運作。

目前 V1 主要驗證 alert state，外部 Email / Slack notification 不列入主要範圍。

---

## Automated Testing

專案使用 pytest。

測試使用獨立 PostgreSQL database：

```text
observability_test
```

目前測試包含：

- Asset invalid status validation
- Asset creation and persistence
- Health endpoint
- Incident valid status transition
- Incident invalid status transition

目前 regression test：

```text
5 passed
```

執行：

```bash
python -m pytest -v
```

---

## Development Dependencies

Production runtime dependencies：

```text
requirements.txt
```

Testing / development dependencies：

```text
requirements-dev.txt
```

安裝 development dependencies：

```bash
pip install -r requirements-dev.txt
```

`requirements-dev.txt` 會先安裝 production dependencies，再加入：

```text
pytest
httpx
```

---

## Continuous Integration

GitHub Actions CI 會在以下事件自動執行：

```text
push
pull_request
```

目前 pipeline：

```text
GitHub Runner
      ↓
PostgreSQL 17 service
      ↓
Create observability_test
      ↓
Apply db/schema.sql
      ↓
Python 3.12
      ↓
Install requirements-dev.txt
      ↓
Run pytest
      ↓
Build Docker image
```

CI 已經在 GitHub Actions 的乾淨 runner 上實際執行成功。

這可以驗證：

```text
Tests pass outside local machine
+
Database schema can initialize correctly
+
Docker image can build successfully
```

---

## Docker

Docker Compose 目前包含：

```text
infra-api
infra-postgres
infra-prometheus
infra-grafana
```

Persistent volume：

```text
postgres_data
prometheus_data
grafana_data
```

因此一般：

```bash
docker compose down
```

不會刪除 database、Prometheus 與 Grafana data。

如果執行：

```bash
docker compose down -v
```

則會刪除 named volumes。

---

## Running Locally

### 1. Start services

```bash
docker compose up -d --build
```

---

### 2. Check containers

```bash
docker compose ps
```

正常情況應看到：

```text
infra-api
infra-postgres
infra-prometheus
infra-grafana
```

PostgreSQL 應為：

```text
healthy
```

---

## Service URLs

### FastAPI

```text
http://localhost:8000
```

### Prometheus

```text
http://localhost:9090
```

### Prometheus Targets

```text
http://localhost:9090/targets
```

### Grafana

```text
http://localhost:3000
```

---

## Health Check

Liveness：

```bash
curl http://localhost:8000/health
```

正常：

```json
{
  "status": "ok"
}
```

Readiness：

```bash
curl http://localhost:8000/ready
```

PostgreSQL 正常時：

```json
{
  "status": "ready"
}
```

---

## Load Testing

如果需要 seed data：

```bash
python scripts/seed_data.py
```

執行 telemetry generator：

```bash
python scripts/telemetry_generator.py
```

PowerShell 調整 concurrency：

```powershell
$env:MAX_WORKERS="20"
python scripts/telemetry_generator.py
```

也可以調整：

```text
INTERVAL_SECONDS
ASSET_LIMIT
```

---

## Project Structure

```text
infra-observability-platform/
│
├── app/
│   ├── main.py
│   └── db.py
│
├── db/
│   └── schema.sql
│
├── monitoring/
│   ├── prometheus.yml
│   │
│   └── grafana/
│       ├── dashboards/
│       │   └── api-observability-dashboard.json
│       │
│       └── provisioning/
│           ├── dashboards/
│           │   └── dashboard.yml
│           │
│           └── datasources/
│               └── prometheus.yml
│
├── scripts/
│   ├── db_connection_benchmark.py
│   ├── seed_data.py
│   └── telemetry_generator.py
│
├── tests/
│   ├── conftest.py
│   ├── test_assets.py
│   ├── test_health.py
│   └── test_incidents.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Technology Stack

### Backend

```text
Python 3.12
FastAPI
```

### Database

```text
PostgreSQL 17
psycopg
psycopg-pool
```

### Testing

```text
pytest
FastAPI TestClient
```

### Container

```text
Docker
Docker Compose
```

### Observability

```text
Prometheus
Grafana
PromQL
```

### CI

```text
GitHub Actions
```

### Version Control

```text
Git
GitHub
```

---

## V1 Scope

目前 V1 完成範圍：

```text
Backend API
PostgreSQL schema
Connection pooling
Docker / Docker Compose
Automated tests
Telemetry generation
Concurrent load testing
Database connection benchmark
Performance investigation
Prometheus instrumentation
PromQL
Grafana Dashboard
Grafana provisioning
Failure simulation
Readiness testing
Alerting
Recovery testing
GitHub Actions CI
```

V1 的目標是先建立完整的：

```text
Application
→ Database
→ Load
→ Metrics
→ Monitoring
→ Alert
→ Failure
→ Recovery
→ CI
```

工程流程。

---

## V2 Roadmap

後續可能擴充：

```text
AWS deployment
Terraform
Go telemetry agent
Kubernetes
CI/CD deployment
Grafana Loki
Grafana Tempo
SLO / SLI based alerting
Redis
Kafka
```


