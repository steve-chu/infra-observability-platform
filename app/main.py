from typing import Literal
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from psycopg.errors import UniqueViolation, ForeignKeyViolation
import psycopg
from app.db import get_connection

app = FastAPI()

#type check, word len check, str white space strip
class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=100)
    @field_validator("name","location", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()

        return value


class AssetCreate(BaseModel):
    site_id: int = Field(gt=0)
    asset_name: str = Field(min_length=1, max_length=50)
    asset_type: str = Field(min_length=1, max_length=50)
    status: Literal["healthy", "degraded", "unhealthy", "maintenance"] = "healthy"
    
    @field_validator("asset_name", "asset_type", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

class AssetStatusUpdate(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy", "maintenance"]

class MetricCreate(BaseModel):
    asset_id: int = Field(gt=0)
    metric_type: str = Field(min_length=1, max_length=50)
    metric_value: float

    @field_validator("metric_type", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

class IncidentCreate(BaseModel):
    asset_id: int = Field(gt=0)
    incident_type: str = Field(min_length=1, max_length=50)
    severity: Literal["low", "medium", "high", "critical"]
    message: str | None = None

    @field_validator("incident_type", "message", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

class IncidentStatusUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved", "closed"]


#http connection check
@app.get("/health")
def health():
    return {"status": "ok"}

#get api db connection status
@app.get("/ready")
def readiness():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        return {"status":"ready"}

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database is not ready"
        )



# get sites data
@app.get("/sites")
def get_sites():

    #build conn between API n postgre, use with auto close channel
    with get_connection() as conn:

        #SQL command sender
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT site_id, name, location FROM sites ORDER BY site_id;"
            )
            sites = cursor.fetchall()

    return sites


#build site sucessfully with code 201, SiteCreate site input n white space check
@app.post("/sites", status_code=201)
def create_site(site: SiteCreate):

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sites (name, location)
                    VALUES (%s, %s)
                    RETURNING site_id, name, location; 
                    """,
                    (site.name, site.location)
                )
                new_site = cursor.fetchone()

    # only catch error violate the uniq rule n return 409
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Site already exiests"
        )
    
    return new_site


@app.get("/sites/{site_id}")
def get_site(site_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT site_id, name, location FROM sites WHERE site_id = %s;",
                (site_id,)
            )
            site = cursor.fetchone()

            if site is None: #empty result catch
                raise HTTPException(
                    status_code=404,
                    detail="Site not found"
                )
            
    return site

#create assets with AssetCreate input value check n whitespace remove
@app.post("/assets", status_code=201)
def create_asset(asset: AssetCreate):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO assets (site_id, asset_name, asset_type, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING asset_id, site_id, asset_name, asset_type, status, created_at, updated_at;
                    """,
                    (
                        asset.site_id,
                        asset.asset_name,
                        asset.asset_type,
                        asset.status
                    )
                )

                new_asset = cursor.fetchone()

    #catch when site value not exist
    except ForeignKeyViolation:
        raise HTTPException(
            status_code=404,
            detail="Site not found"
        )

    #catch when site n name not unique pair
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Asset already exists in this site"
        )
    
    return new_asset


@app.get("/assets")
#optional input site_id n status 
def get_assets(
    site_id: int | None = None,
    status: Literal["healthy", "degraded", "unhealthy", "maintenance"] | None = None
    ):
    with get_connection() as conn:
        with conn.cursor() as cursor:

            #use dynamic query clause for SQL query use
            conditions = []
            params = []

            if site_id is not None:
                conditions.append("site_id = %s")
                params.append(site_id)

            if status is not None:
                conditions.append("status = %s")
                params.append(status)

            where_clause = ""

            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)

            query = f"""
            SELECT asset_id, site_id, asset_name, asset_type, status, created_at, updated_at
            FROM assets
            {where_clause}
            ORDER BY asset_id;
            """

            cursor.execute(query, params)

            assets = cursor.fetchall()
    return assets


@app.get("/assets/{asset_id}")
def get_asset(asset_id: int):

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT asset_id, site_id, asset_name, asset_type, status, created_at, updated_at
                FROM assets
                WHERE asset_id = %s;
                """,
                (asset_id,)
            )
           
            asset = cursor.fetchone()

    if asset is None: #asset not found error handling
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )
    
    return asset

#modify asset status
@app.patch("/assets/{asset_id}/status")
def update_asset_status(asset_id: int, update: AssetStatusUpdate):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE assets
                SET status = %s,
                    updated_at = NOW()
                WHERE asset_id = %s
                RETURNING asset_id, site_id, asset_name, asset_type, status, created_at, updated_at;
                """,
                (
                    update.status,
                    asset_id
                )
            )
            updated_asset = cursor.fetchone()

            if updated_asset is None:
                raise HTTPException(
                    status_code=404,
                    detail="Asset not found"
                )
    return updated_asset


#upload asset metric
@app.post("/metrics", status_code=201)
def create_metric(metric:MetricCreate):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO metrics (asset_id, metric_type, metric_value)
                    VALUES (%s, %s, %s)
                    RETURNING metric_id, asset_id, metric_type, metric_value, recorded_at;
                    """,
                    (
                        metric.asset_id,
                        metric.metric_type,
                        metric.metric_value
                    )
                )

                new_metric = cursor.fetchone()
    #asset not found handling
    except ForeignKeyViolation:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    return new_metric

#time period search handling
@app.get("/metrics")
def get_metrics(
    asset_id: int | None = None,
    metric_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None
    ):
        if (
            start_time is not None
            and end_time is not None
            and start_time > end_time
        ):
            raise HTTPException(
                status_code=400,
                detail="start_time must be before end_time"
            )

        with get_connection() as conn:
            with conn.cursor() as cursor:
                conditions = []
                params = []

                if asset_id is not None:
                    conditions.append("asset_id = %s")
                    params.append(asset_id)

                if metric_type is not None:
                    conditions.append("metric_type = %s")
                    params.append(metric_type)

                if start_time is not None:
                    conditions.append("recorded_at >= %s")
                    params.append(start_time)

                if end_time is not None:
                    conditions.append("recorded_at <= %s")
                    params.append(end_time)


                where_clause = ""

                if conditions:
                    where_clause = " WHERE " + " AND ".join(conditions) 

                query = f"""
                SELECT metric_id, asset_id, metric_type, metric_value, recorded_at
                FROM metrics
                {where_clause}
                ORDER BY recorded_at DESC

                """             
                
                cursor.execute(query, params)
                metrics = cursor.fetchall()
        return metrics

@app.post("/incidents", status_code=201)
def create_incident(incident: IncidentCreate):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO incidents (
                        asset_id,
                        incident_type,
                        severity,
                        message
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING
                        incident_id,
                        asset_id,
                        incident_type,
                        severity,
                        status,
                        message,
                        detected_at,
                        resolved_at;
                    """,
                    (
                        incident.asset_id,
                        incident.incident_type,
                        incident.severity,
                        incident.message
                    )
                )

                new_incident = cursor.fetchone()
    except ForeignKeyViolation:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )
    return new_incident


@app.get("/incidents")
def get_incidents(
    asset_id: int | None = None,
    severity: Literal["low", "medium", "high", "critical"] | None = None,
    status: Literal["open", "investigating", "resolved", "closed"] | None = None
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            conditions = []
            params = []

            if asset_id is not None:
                conditions.append("asset_id = %s")
                params.append(asset_id)

            if severity is not None:
                conditions.append("severity = %s")
                params.append(severity)

            if status is not None:
                conditions.append("status = %s")
                params.append(status)

            where_clause = ""

            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)

            query = f"""
            SELECT incident_id, asset_id, incident_type, severity, status, message, detected_at, resolved_at
            FROM incidents
            {where_clause}
            ORDER BY detected_at DESC;
            """

            cursor.execute(query, params)
            incidents = cursor.fetchall()

    return incidents

#modify incident status with conditions
@app.patch("/incidents/{incident_id}/status")
def update_incident_status(
    incident_id: int,
    update: IncidentStatusUpdate
):
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT incident_id, status
                FROM incidents
                WHERE incident_id = %s;
                """,
                (incident_id,)
            )

            incident = cursor.fetchone()

            # check if incident exists
            if incident is None:
                raise HTTPException(
                    status_code=404,
                    detail="Incident not found"
                )
            current_status = incident["status"]
            #rule for incident transitioning
            allowed_transitions = {
                "open": {"investigating"},
                "investigating": {"resolved"},
                "resolved": {"closed"},
                "closed": set()
            }

            if update.status not in allowed_transitions[current_status]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot change incident status from {current_status} to {update.status}"
                )

            cursor.execute(
                """
                UPDATE incidents
                SET status = %s,
                    resolved_at = CASE
                        WHEN %s = 'resolved' THEN NOW()
                        ELSE resolved_at
                    END
                WHERE incident_id = %s
                RETURNING incident_id, asset_id, incident_type, severity, status, message, detected_at, resolved_at;
                """,
                (
                    update.status,
                    update.status,
                    incident_id
                )
            )
    
            updated_incident = cursor.fetchone()
    return updated_incident
