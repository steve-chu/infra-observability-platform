from fastapi import FastAPI, HTTPException
from app.db import get_connection
from pydantic import BaseModel, Field, field_validator
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

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

#http connection check
@app.get("/health")

def health():
    return {"status": "ok"}

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

#build sucessfully with code 201
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

            if site is None:
                raise HTTPException(
                    status_code=404,
                    detail="Site not found"
                )
            
    return site
