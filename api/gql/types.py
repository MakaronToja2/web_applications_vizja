import strawberry
from datetime import datetime


@strawberry.type
class ServerType:
    id: int
    server_id: str
    name: str
    status: str
    cpu: float | None
    mem: float | None
    last_heartbeat: datetime | None
    created_at: datetime


@strawberry.type
class AlertRuleType:
    id: int
    name: str
    metric: str
    operator: str
    threshold: float
    server_id: str | None
    enabled: bool


@strawberry.type
class AlertType:
    id: int
    rule_name: str
    server_id: str
    message: str
    timestamp: datetime


@strawberry.type
class StatsType:
    total_servers: int
    servers_up: int
    servers_down: int
    servers_unknown: int
    total_alerts: int
