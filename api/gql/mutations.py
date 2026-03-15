import strawberry
from gql.types import AlertRuleType
from database import SessionLocal
from models import AlertRule, Alert, Server, Heartbeat, Incident


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_alert_rule(
        self,
        name: str,
        metric: str,
        operator: str,
        threshold: float,
        server_id: str | None = None,
    ) -> AlertRuleType:
        db = SessionLocal()
        try:
            rule = AlertRule(
                name=name,
                metric=metric,
                operator=operator,
                threshold=threshold,
                server_id=server_id,
                enabled=True,
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return AlertRuleType(
                id=rule.id, name=rule.name, metric=rule.metric,
                operator=rule.operator, threshold=rule.threshold,
                server_id=rule.server_id, enabled=rule.enabled,
            )
        finally:
            db.close()

    @strawberry.mutation
    def delete_alert_rule(self, id: int) -> bool:
        db = SessionLocal()
        try:
            rule = db.query(AlertRule).filter(AlertRule.id == id).first()
            if not rule:
                return False
            db.delete(rule)
            db.commit()
            return True
        finally:
            db.close()

    @strawberry.mutation
    def toggle_alert_rule(self, id: int, enabled: bool) -> AlertRuleType | None:
        db = SessionLocal()
        try:
            rule = db.query(AlertRule).filter(AlertRule.id == id).first()
            if not rule:
                return None
            rule.enabled = enabled
            db.commit()
            db.refresh(rule)
            return AlertRuleType(
                id=rule.id, name=rule.name, metric=rule.metric,
                operator=rule.operator, threshold=rule.threshold,
                server_id=rule.server_id, enabled=rule.enabled,
            )
        finally:
            db.close()

    @strawberry.mutation
    def delete_server(self, server_id: str) -> bool:
        """Delete a server and all its heartbeats/incidents."""
        db = SessionLocal()
        try:
            server = db.query(Server).filter(Server.server_id == server_id).first()
            if not server:
                return False
            db.query(Heartbeat).filter(Heartbeat.server_id == server_id).delete()
            db.query(Incident).filter(Incident.server_id == server_id).delete()
            db.query(Alert).filter(Alert.server_id == server_id).delete()
            db.delete(server)
            db.commit()
            return True
        finally:
            db.close()

    @strawberry.mutation
    def clear_alerts(self) -> int:
        """Delete all alerts. Returns number of deleted alerts."""
        db = SessionLocal()
        try:
            count = db.query(Alert).delete()
            db.commit()
            return count
        finally:
            db.close()
