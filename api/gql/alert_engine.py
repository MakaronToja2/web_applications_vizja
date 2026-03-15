"""
Alert Engine — evaluates user-defined rules against incoming heartbeat data.
If a rule matches, creates an Alert record and publishes to GraphQL subscriptions.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from models import AlertRule, Alert
from gql.types import AlertType
from gql.subscriptions import publish_alert

OPERATORS = {
    ">": lambda val, thr: val > thr,
    "<": lambda val, thr: val < thr,
    ">=": lambda val, thr: val >= thr,
    "<=": lambda val, thr: val <= thr,
    "==": lambda val, thr: val == thr,
    "!=": lambda val, thr: val != thr,
}


async def evaluate_rules(server_id: str, cpu: float, mem: float, status: str, db: Session):
    """Check all enabled rules against the given metrics."""
    rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()

    metrics = {
        "cpu": cpu,
        "mem": mem,
        "status": 0.0 if status == "DOWN" else 1.0,
    }

    for rule in rules:
        if rule.server_id and rule.server_id != server_id:
            continue

        value = metrics.get(rule.metric)
        if value is None:
            continue

        op_func = OPERATORS.get(rule.operator)
        if not op_func:
            continue

        if op_func(value, rule.threshold):
            now = datetime.utcnow()
            message = f"{rule.metric} {rule.operator} {rule.threshold} (actual: {value})"

            alert = Alert(
                rule_name=rule.name,
                server_id=server_id,
                message=message,
                timestamp=now,
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)

            await publish_alert(AlertType(
                id=alert.id,
                rule_name=rule.name,
                server_id=server_id,
                message=message,
                timestamp=now,
            ))
