from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")  # UP, DOWN, UNKNOWN
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cpu: Mapped[float | None] = mapped_column(Float, nullable=True)
    mem: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[str] = mapped_column(String(100), ForeignKey("servers.server_id"), index=True)
    cpu: Mapped[float] = mapped_column(Float)
    mem: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[str] = mapped_column(String(100), ForeignKey("servers.server_id"), index=True)
    event_type: Mapped[str] = mapped_column(String(20))  # DOWN, UP
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    metric: Mapped[str] = mapped_column(String(20))   # cpu, mem, status
    operator: Mapped[str] = mapped_column(String(5))   # >, <, >=, <=, ==, !=
    threshold: Mapped[float] = mapped_column(Float)
    server_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # None = all servers
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(200))
    server_id: Mapped[str] = mapped_column(String(100), index=True)
    message: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
