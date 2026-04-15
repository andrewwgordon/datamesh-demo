"""
EAM Simulator Service
Provides REST API to create and update Assets and WorkOrders.
Writes to Postgres database.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import psycopg2
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EAM Simulator", version="1.0.0")

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "eam")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


# Pydantic models
class AssetCreate(BaseModel):
    asset_id: str = Field(..., description="Unique asset identifier")
    name: str = Field(..., description="Asset name")
    type: str = Field(..., description="Asset type")
    location: Optional[str] = Field(None, description="Asset location")


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None


class WorkOrderCreate(BaseModel):
    work_order_id: str = Field(..., description="Unique work order identifier")
    asset_id: str = Field(..., description="Associated asset ID")
    description: str = Field(..., description="Work order description")
    status: str = Field(default="OPEN", description="Work order status")
    priority: Optional[str] = Field("MEDIUM", description="Work order priority")


class WorkOrderUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


# Asset endpoints
@app.post("/assets", tags=["Assets"])
def create_asset(asset: AssetCreate):
    """Create a new asset."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO asset (asset_id, name, type, location)
                VALUES (%s, %s, %s, %s)
                """,
                (asset.asset_id, asset.name, asset.type, asset.location)
            )
        conn.commit()
        logger.info(f"Created asset: {asset.asset_id}")
        return {"message": "Asset created", "asset_id": asset.asset_id}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Asset already exists")
    finally:
        conn.close()


@app.get("/assets/{asset_id}", tags=["Assets"])
def get_asset(asset_id: str):
    """Get asset by ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT asset_id, name, type, location FROM asset WHERE asset_id = %s",
                (asset_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Asset not found")
            return {
                "asset_id": row[0],
                "name": row[1],
                "type": row[2],
                "location": row[3]
            }
    finally:
        conn.close()


@app.put("/assets/{asset_id}", tags=["Assets"])
def update_asset(asset_id: str, asset_update: AssetUpdate):
    """Update an existing asset."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Build dynamic update query
            updates = []
            values = []
            if asset_update.name is not None:
                updates.append("name = %s")
                values.append(asset_update.name)
            if asset_update.type is not None:
                updates.append("type = %s")
                values.append(asset_update.type)
            if asset_update.location is not None:
                updates.append("location = %s")
                values.append(asset_update.location)
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            values.append(asset_id)
            query = f"UPDATE asset SET {', '.join(updates)} WHERE asset_id = %s"
            cur.execute(query, values)
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Asset not found")
        
        conn.commit()
        logger.info(f"Updated asset: {asset_id}")
        return {"message": "Asset updated", "asset_id": asset_id}
    finally:
        conn.close()


# WorkOrder endpoints
@app.post("/work-orders", tags=["WorkOrders"])
def create_work_order(work_order: WorkOrderCreate):
    """Create a new work order."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if asset exists
            cur.execute("SELECT 1 FROM asset WHERE asset_id = %s", (work_order.asset_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=400, detail="Referenced asset does not exist")
            
            cur.execute(
                """
                INSERT INTO work_order (work_order_id, asset_id, description, status, priority)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (work_order.work_order_id, work_order.asset_id, work_order.description, 
                 work_order.status, work_order.priority)
            )
        conn.commit()
        logger.info(f"Created work order: {work_order.work_order_id}")
        return {"message": "Work order created", "work_order_id": work_order.work_order_id}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Work order already exists")
    finally:
        conn.close()


@app.get("/work-orders/{work_order_id}", tags=["WorkOrders"])
def get_work_order(work_order_id: str):
    """Get work order by ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT work_order_id, asset_id, description, status, priority
                FROM work_order WHERE work_order_id = %s
                """,
                (work_order_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Work order not found")
            return {
                "work_order_id": row[0],
                "asset_id": row[1],
                "description": row[2],
                "status": row[3],
                "priority": row[4]
            }
    finally:
        conn.close()


@app.put("/work-orders/{work_order_id}", tags=["WorkOrders"])
def update_work_order(work_order_id: str, work_order_update: WorkOrderUpdate):
    """Update an existing work order."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Build dynamic update query
            updates = []
            values = []
            if work_order_update.description is not None:
                updates.append("description = %s")
                values.append(work_order_update.description)
            if work_order_update.status is not None:
                updates.append("status = %s")
                values.append(work_order_update.status)
            if work_order_update.priority is not None:
                updates.append("priority = %s")
                values.append(work_order_update.priority)
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            values.append(work_order_id)
            query = f"UPDATE work_order SET {', '.join(updates)} WHERE work_order_id = %s"
            cur.execute(query, values)
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Work order not found")
        
        conn.commit()
        logger.info(f"Updated work order: {work_order_id}")
        return {"message": "Work order updated", "work_order_id": work_order_id}
    finally:
        conn.close()


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
