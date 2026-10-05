# Distributed Infrastructure Observability & Incident Management Platform

## Goal

Build a production-like backend and SRE platform for:

- infrastructure asset management
- telemetry ingestion
- health monitoring
- incident management
- load testing
- observability
- failure simulation
- cloud deployment

## Current Architecture

```text
Client
  ↓
FastAPI Container
  ↓
PostgreSQL Container
  ↓
Persistent Docker Volume
```

The services are currently running with Docker Compose.

## Implemented

### APIs

- `GET /health`
- `GET /ready`
- `GET /sites`
- `POST /sites`
- `GET /sites/{site_id}`
- `GET /assets`
- `POST /assets`
- `GET /assets/{asset_id}`
- `PATCH /assets/{asset_id}/status`
- `GET /metrics`
- `POST /metrics`
- `GET /incidents`
- `POST /incidents`
- `PATCH /incidents/{incident_id}/status`

### Backend

- FastAPI
- PostgreSQL 17
- psycopg
- raw SQL
- request validation
- asset filtering
- metric time-range filtering
- incident status flow
- database health/readiness checks

### Testing

- pytest
- FastAPI TestClient
- separate test database
- fixture setup and cleanup
- asset persistence integration test
- incident state transition tests

### Docker

- FastAPI Dockerfile
- PostgreSQL container
- Docker Compose
- container-to-container networking
- persistent PostgreSQL volume

## Incident Flow

```text
open
  ↓
investigating
  ↓
resolved
  ↓
closed
```

Invalid transitions return `409 Conflict`.

## Current Stack

- Python 3.12
- FastAPI
- PostgreSQL
- psycopg
- pytest
- Docker
- Docker Compose
- Git / GitHub

## Next Steps

- telemetry generator
- high-volume metric ingestion
- load testing
- database performance tuning
- Prometheus and Grafana
- logging and tracing
- failure simulation
- CI/CD
- AWS
- Terraform
- Kubernetes
