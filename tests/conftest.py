import os
os.environ["DB_NAME"] = "observability_test" #switch use to test db 

import pytest
from app.db import get_connection

#create temp site for testing config
@pytest.fixture
def test_site():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sites (name, location)
                VALUES (%s, %s)
                RETURNING site_id, name, location;
                """,
                (
                    "TEST_SITE",
                    "TEST_LOCATION"
                )
            )
            site = cursor.fetchone()

    #pass data to test function, will clean up after test done
    yield site 

    #clean up test data, start from FK child asset data than site data
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM assets WHERE site_id = %s;",
                (site["site_id"],)
            )
            cursor.execute(
                "DELETE FROM sites WHERE site_id = %s;",
                (site["site_id"],)
            )

#create temp site and asset for testing config
@pytest.fixture
def test_asset(test_site):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO assets (site_id, asset_name, asset_type, status)
                VALUES (%s, %s, %s, %s)
                RETURNING asset_id, site_id, asset_name, asset_type, status;
                """,
                (
                    test_site["site_id"],
                    "TEST_INCIDENT_ASSET",
                    "server",
                    "healthy"
                )
            )

            asset = cursor.fetchone()

    yield asset #hold til test done, than delete temp db data

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM incidents WHERE asset_id = %s;",
                (asset["asset_id"],)
            )

            cursor.execute(
                "DELETE FROM assets WHERE asset_id = %s;",
                (asset["asset_id"],)
            )