"""
REST API — Person 2

FastAPI application serving the Watchdog monitoring API over HTTPS.
Provides CRUD for servers and exposes heartbeat history and stats.
"""

import threading
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine, get_db, Base
from models import Server, Heartbeat, Incident
from consumer import start_consumer


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
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Start RabbitMQ consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()
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


# --- Endpoints ---

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
