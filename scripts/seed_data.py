import os
import httpx

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000"
)

#create sites
def create_site(name, location):
    response = httpx.post(
        f"{API_BASE_URL}/sites",
        json={
            "name": name,
            "location": location
        },
        timeout=5.0
    )

    #if response error raise exception
    response.raise_for_status()

    return response.json()

#create assets
def create_asset(site_id, asset_name, asset_type="server"):
    response = httpx.post(
        f"{API_BASE_URL}/assets",
        json={
            "site_id": site_id,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "status": "healthy"
        },
        timeout=5.0
    )

    response.raise_for_status()

    return response.json()

sites = [
    ("TAIPEI_SITE", "Taipei"),
    ("HSINCHU_SITE", "Hsinchu"),
    ("TAOYUAN_SITE", "Taoyuan"),
]

#create each sites 10 assets
for site_name, location in sites:
    site = create_site(site_name, location)

    for i in range(1, 11):
        asset_name = f"{site_name}-SERVER-{i:02d}"

        asset = create_asset(
            site["site_id"],
            asset_name
        )

        print(f"Create asset: {asset['asset_name']}")