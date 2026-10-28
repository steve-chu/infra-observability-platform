from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_metrics_rejects_limit_over_maximum():
    response = client.get("/metrics", params={"limit": 2000})

    assert response.status_code == 422