import strawberry
from gql.types import ServerType, AlertRuleType, AlertType, StatsType
from database import SessionLocal
from models import Server, AlertRule, Alert
from sqlalchemy import func


@strawberry.type
class Query:
    @strawberry.field
    def servers(self) -> list[ServerType]:
        db = SessionLocal()
        try:
            rows = db.query(Server).all()
            return [
                ServerType(
                    id=r.id, server_id=r.server_id, name=r.name, status=r.status,
                    cpu=r.cpu, mem=r.mem, last_heartbeat=r.last_heartbeat,
                    created_at=r.created_at,
                )
                for r in rows
            ]
        finally:
            db.close()

    @strawberry.field
    def server(self, server_id: str) -> ServerType | None:
        db = SessionLocal()
        try:
            r = db.query(Server).filter(Server.server_id == server_id).first()
            if not r:
                return None
            return ServerType(
                id=r.id, server_id=r.server_id, name=r.name, status=r.status,
                cpu=r.cpu, mem=r.mem, last_heartbeat=r.last_heartbeat,
                created_at=r.created_at,
            )
        finally:
            db.close()

    @strawberry.field
    def alert_rules(self) -> list[AlertRuleType]:
        db = SessionLocal()
        try:
            rows = db.query(AlertRule).all()
            return [
                AlertRuleType(
                    id=r.id, name=r.name, metric=r.metric, operator=r.operator,
                    threshold=r.threshold, server_id=r.server_id, enabled=r.enabled,
                )
                for r in rows
            ]
        finally:
            db.close()

    @strawberry.field
    def alerts(self, limit: int = 50) -> list[AlertType]:
        db = SessionLocal()
        try:
            rows = db.query(Alert).order_by(Alert.timestamp.desc()).limit(limit).all()
            return [
                AlertType(
                    id=r.id, rule_name=r.rule_name, server_id=r.server_id,
                    message=r.message, timestamp=r.timestamp,
                )
                for r in rows
            ]
        finally:
            db.close()

    @strawberry.field
    def stats(self) -> StatsType:
        db = SessionLocal()
        try:
            total = db.query(func.count(Server.id)).scalar()
            up = db.query(func.count(Server.id)).filter(Server.status == "UP").scalar()
            down = db.query(func.count(Server.id)).filter(Server.status == "DOWN").scalar()
            unknown = db.query(func.count(Server.id)).filter(Server.status == "UNKNOWN").scalar()
            total_alerts = db.query(func.count(Alert.id)).scalar()
            return StatsType(
                total_servers=total, servers_up=up, servers_down=down,
                servers_unknown=unknown, total_alerts=total_alerts,
            )
        finally:
            db.close()
