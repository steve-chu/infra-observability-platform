from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)

def test_create_asset_rejects_invalid_status():
    response = client.post(
        "/assets",
        json={
            "site_id": 13,
            "asset_name": "test-server",
            "asset_type": "server",
            "status": "banana"
        }
    )
   
    assert response.status_code == 422  #illegal status input 
    errors = response.json()["detail"]
    assert errors[0]["loc"][-1] == "status" #error point validate


#test create asset, firstly create test site from conftest.py than insert site data
def test_create_asset(test_site):
    response = client.post(
        "/assets",
        json={
            "site_id": test_site["site_id"], 
            "asset_name": "TEST_ASSET",
            "asset_type": "server",
            "status": "healthy"
        }
    )
    #check post response
    assert response.status_code == 201

    body = response.json()
    
    assert body["site_id"] == test_site["site_id"]  #check if site_id are match 
    assert body["asset_name"] == "TEST_ASSET"
    assert body["asset_type"] == "server"
    assert body["status"] == "healthy"

    #than get the id create by database 
    asset_id = body["asset_id"]

    #check get asset_id avalibility 
    get_response = client.get(f"/assets/{asset_id}")

    assert get_response.status_code == 200

    saved_asset = get_response.json() #save the get body

    #verify asset data
    assert saved_asset["asset_id"] == asset_id
    assert saved_asset["site_id"] == test_site["site_id"]
    assert saved_asset["asset_name"] == "TEST_ASSET"
    assert saved_asset["asset_type"] == "server"
    assert saved_asset["status"] == "healthy"