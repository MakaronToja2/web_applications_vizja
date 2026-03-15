"""
REST API — Watchdog

FastAPI application serving the Watchdog monitoring API over HTTPS.
REST endpoints handle data ingestion from TCP server.
GraphQL (Strawberry) handles all frontend queries, mutations, and subscriptions.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import Server, Heartbeat, Incident


# --- Pydantic schemas ---

class HeartbeatPayload(BaseModel):
    server_id: str
    cpu: float
    mem: float
    status: str = "OK"
    timestamp: str | None = None


class StatusPayload(BaseModel):
    server_id: str
    status: str  # "DOWN" or "UP"


# --- App setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Watchdog API",
    description="API do monitorowania statusu serwerów",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GraphQL ---
from gql.schema import graphql_router
from gql.alert_engine import evaluate_rules
from gql.subscriptions import publish_status_change
from gql.types import ServerType

app.include_router(graphql_router, prefix="/graphql")


# --- REST endpoints: data ingestion (used by TCP Server) ---

@app.post("/api/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload, db: Session = Depends(get_db)):
    """Receive heartbeat from TCP server. Auto-registers unknown servers."""
    now = datetime.utcnow()

    # Upsert server
    server = db.query(Server).filter(Server.server_id == payload.server_id).first()
    if not server:
        server = Server(server_id=payload.server_id, name=payload.server_id)
        db.add(server)

    server.status = "UP"
    server.last_heartbeat = now
    server.cpu = payload.cpu
    server.mem = payload.mem

    # Record heartbeat
    heartbeat = Heartbeat(
        server_id=payload.server_id,
        cpu=payload.cpu,
        mem=payload.mem,
        status=payload.status,
        timestamp=now,
    )
    db.add(heartbeat)
    db.commit()

    await evaluate_rules(payload.server_id, payload.cpu, payload.mem, "UP", db)

    # Push live heartbeat data to WebSocket subscribers
    await publish_status_change(ServerType(
        id=server.id,
        server_id=server.server_id,
        name=server.name,
        status="UP",
        cpu=payload.cpu,
        mem=payload.mem,
        last_heartbeat=now,
        created_at=server.created_at,
    ))

    return {"ok": True}


@app.post("/api/status")
async def receive_status_change(payload: StatusPayload, db: Session = Depends(get_db)):
    """Receive status change (DOWN/UP) from TCP server."""
    now = datetime.utcnow()

    server = db.query(Server).filter(Server.server_id == payload.server_id).first()
    if not server:
        server = Server(server_id=payload.server_id, name=payload.server_id)
        db.add(server)

    server.status = payload.status

    # Record incident
    incident = Incident(
        server_id=payload.server_id,
        event_type=payload.status,
        timestamp=now,
    )
    db.add(incident)
    db.commit()

    await evaluate_rules(payload.server_id, server.cpu or 0, server.mem or 0, payload.status, db)

    # Push status change to WebSocket subscribers
    await publish_status_change(ServerType(
        id=server.id,
        server_id=server.server_id,
        name=server.name,
        status=payload.status,
        cpu=server.cpu,
        mem=server.mem,
        last_heartbeat=server.last_heartbeat,
        created_at=server.created_at,
    ))

    return {"ok": True}
