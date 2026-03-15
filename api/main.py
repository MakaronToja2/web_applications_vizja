"""
REST API — Watchdog

FastAPI application serving the Watchdog monitoring API over HTTPS.
Provides CRUD for servers, heartbeat ingestion, and status updates.
GraphQL (Strawberry) is mounted at /graphql by TODO.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine, get_db, Base
from models import Server, Heartbeat, Incident


# --- Pydantic schemas ---

class ServerCreate(BaseModel):
    server_id: str
    name: str = ""


class ServerResponse(BaseModel):
    id: int
    server_id: str
    name: str
    status: str
    last_heartbeat: datetime | None
    cpu: float | None
    mem: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class HeartbeatPayload(BaseModel):
    server_id: str
    cpu: float
    mem: float
    status: str = "OK"
    timestamp: str | None = None


class StatusPayload(BaseModel):
    server_id: str
    status: str  # "DOWN" or "UP"


class HeartbeatResponse(BaseModel):
    id: int
    server_id: str
    cpu: float
    mem: float
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True


class IncidentResponse(BaseModel):
    id: int
    server_id: str
    event_type: str
    timestamp: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_servers: int
    servers_up: int
    servers_down: int
    servers_unknown: int
    total_incidents: int


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

# --- GraphQL (TODO mounts this) ---
# Uncomment when TODO creates api/graphql/schema.py:
# from graphql.schema import graphql_router
# app.include_router(graphql_router, prefix="/graphql")


# --- Endpoints: data ingestion (used by TCP Server) ---

@app.post("/api/heartbeat")
def receive_heartbeat(payload: HeartbeatPayload, db: Session = Depends(get_db)):
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

    # TODO: TODO — call alert engine here
    # from graphql.alert_engine import evaluate_rules
    # evaluate_rules(payload.server_id, payload.cpu, payload.mem, "UP", db)

    return {"ok": True}


@app.post("/api/status")
def receive_status_change(payload: StatusPayload, db: Session = Depends(get_db)):
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

    # TODO: TODO — call alert engine / emit subscription event here
    # from graphql.alert_engine import evaluate_rules
    # evaluate_rules(payload.server_id, server.cpu or 0, server.mem or 0, payload.status, db)

    return {"ok": True}


# --- Endpoints: CRUD (used by dashboard / external clients) ---

@app.post("/api/servers", response_model=ServerResponse, status_code=201)
def register_server(server: ServerCreate, db: Session = Depends(get_db)):
    existing = db.query(Server).filter(Server.server_id == server.server_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Serwer o tym ID już istnieje")
    new_server = Server(
        server_id=server.server_id,
        name=server.name or server.server_id,
    )
    db.add(new_server)
    db.commit()
    db.refresh(new_server)
    return new_server


@app.get("/api/servers", response_model=list[ServerResponse])
def list_servers(db: Session = Depends(get_db)):
    return db.query(Server).all()


@app.get("/api/servers/{server_id}", response_model=ServerResponse)
def get_server(server_id: str, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.server_id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Nie znaleziono serwera")
    return server


@app.delete("/api/servers/{server_id}", status_code=204)
def delete_server(server_id: str, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.server_id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Nie znaleziono serwera")
    db.delete(server)
    db.commit()


@app.get("/api/servers/{server_id}/history", response_model=list[HeartbeatResponse])
def get_server_history(server_id: str, limit: int = 100, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.server_id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Nie znaleziono serwera")
    return (
        db.query(Heartbeat)
        .filter(Heartbeat.server_id == server_id)
        .order_by(Heartbeat.timestamp.desc())
        .limit(limit)
        .all()
    )


@app.get("/api/servers/{server_id}/incidents", response_model=list[IncidentResponse])
def get_server_incidents(server_id: str, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.server_id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Nie znaleziono serwera")
    return (
        db.query(Incident)
        .filter(Incident.server_id == server_id)
        .order_by(Incident.timestamp.desc())
        .all()
    )


@app.get("/api/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Server.id)).scalar()
    up = db.query(func.count(Server.id)).filter(Server.status == "UP").scalar()
    down = db.query(func.count(Server.id)).filter(Server.status == "DOWN").scalar()
    unknown = db.query(func.count(Server.id)).filter(Server.status == "UNKNOWN").scalar()
    incidents = db.query(func.count(Incident.id)).scalar()
    return StatsResponse(
        total_servers=total,
        servers_up=up,
        servers_down=down,
        servers_unknown=unknown,
        total_incidents=incidents,
    )
