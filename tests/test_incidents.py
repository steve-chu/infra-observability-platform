from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

#stutus change validation, should follow the correct step and show 200 
def test_incident_status_flow(test_asset):
    # create incident
    response = client.post(
        "/incidents",
        json={
            "asset_id": test_asset["asset_id"],
            "incident_type": "high_cpu",
            "severity": "high",
            "message": "CPU usage exceeded threshold"
        }
    )

    assert response.status_code == 201

    #get response body
    incident = response.json()

    assert incident["asset_id"] == test_asset["asset_id"]
    assert incident["status"] == "open"

    incident_id = incident["incident_id"]

    # status stage change: open -> investigating
    response = client.patch(
        f"/incidents/{incident_id}/status",
        json={"status": "investigating"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "investigating"

    # status stage change: investigating -> resolved
    response = client.patch(
        f"/incidents/{incident_id}/status",
        json={"status": "resolved"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["resolved_at"] is not None

    # status stage change: resolved -> closed
    response = client.patch(
        f"/incidents/{incident_id}/status",
        json={"status": "closed"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "closed"

#test wrong incident status stage change, should be catch as 409
def test_incident_rejects_invalid_status_transition(test_asset):
    response = client.post(
        "/incidents",
        json={
            "asset_id": test_asset["asset_id"],
            "incident_type": "high_cpu",
            "severity": "high",
            "message": "CPU usage exceeded threshold"
        }
    )

    assert response.status_code == 201

    incident_id = response.json()["incident_id"]

    # Invalid transition: open -> closed   shold be open -> investigating
    response = client.patch(
        f"/incidents/{incident_id}/status",
        json={"status": "closed"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot change incident status from open to closed"
