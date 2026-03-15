# Przewodnik — Osoba 3: GraphQL + Alerty + WebSocket

## Co musisz zaimplementować

Trzy rzeczy wewnątrz backendu (`api/graphql/`) + dashboard:

1. **GraphQL Schema** (Strawberry) — queries, mutations, subscriptions
2. **Silnik alertów** — reguły zdefiniowane przez użytkownika, ewaluowane przy każdym heartbeatcie
3. **Dashboard** — frontend łączący się z GraphQL (queries + subscriptions/WebSocket)

## Architektura twojej części

```
REST API (FastAPI)
    │
    │ heartbeat przychodzi z TCP servera
    │ → ewaluacja reguł alertów
    │ → jeśli reguła spełniona → emit event
    ▼
GraphQL Subscriptions (WebSocket)
    │
    │ push alert do dashboardu
    ▼
Dashboard (przeglądarka)
```

## 1. GraphQL Schema (Strawberry)

Stwórz folder `api/graphql/` z plikami:

### `api/graphql/schema.py` — główny schemat

```python
import strawberry
from strawberry.fastapi import GraphQLRouter
from api.graphql.types import ServerType, AlertRuleType, AlertType, StatsType
from api.graphql.queries import Query
from api.graphql.mutations import Mutation
from api.graphql.subscriptions import Subscription

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)

graphql_router = GraphQLRouter(schema)
```

### `api/graphql/types.py` — typy GraphQL

```python
import strawberry
from datetime import datetime

@strawberry.type
class ServerType:
    server_id: str
    name: str
    status: str
    cpu: float | None
    mem: float | None
    last_heartbeat: datetime | None

@strawberry.type
class AlertRuleType:
    id: int
    name: str
    metric: str          # "cpu", "mem", "status"
    operator: str        # ">", "<", "==", "!="
    threshold: float     # np. 90.0
    server_id: str | None  # None = dotyczy wszystkich serwerów
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
    total_alerts: int
```

### `api/graphql/queries.py` — zapytania

```python
import strawberry
from api.graphql.types import ServerType, AlertRuleType, AlertType, StatsType

@strawberry.type
class Query:
    @strawberry.field
    def servers(self) -> list[ServerType]:
        """Lista wszystkich serwerów z aktualnym statusem."""
        # TODO: pobierz z bazy danych
        ...

    @strawberry.field
    def server(self, server_id: str) -> ServerType | None:
        """Pojedynczy serwer po ID."""
        # TODO: pobierz z bazy danych
        ...

    @strawberry.field
    def alert_rules(self) -> list[AlertRuleType]:
        """Lista reguł alertów."""
        # TODO: pobierz z bazy danych
        ...

    @strawberry.field
    def alerts(self, limit: int = 50) -> list[AlertType]:
        """Ostatnie alerty."""
        # TODO: pobierz z bazy danych
        ...

    @strawberry.field
    def stats(self) -> StatsType:
        """Statystyki systemu."""
        # TODO: policz z bazy danych
        ...
```

### `api/graphql/mutations.py` — mutacje (CRUD reguł)

```python
import strawberry
from api.graphql.types import AlertRuleType

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
        """Utwórz nową regułę alertu.

        Przykłady:
        - name="Wysokie CPU", metric="cpu", operator=">", threshold=90
        - name="Serwer padł", metric="status", operator="==", threshold=0 (0=DOWN)
        - name="Mało RAM", metric="mem", operator=">", threshold=85
        """
        # TODO: zapisz do bazy danych
        ...

    @strawberry.mutation
    def delete_alert_rule(self, id: int) -> bool:
        """Usuń regułę alertu."""
        # TODO: usuń z bazy danych
        ...

    @strawberry.mutation
    def toggle_alert_rule(self, id: int, enabled: bool) -> AlertRuleType:
        """Włącz/wyłącz regułę."""
        # TODO: zaktualizuj w bazie
        ...
```

### `api/graphql/subscriptions.py` — subskrypcje (WebSocket)

```python
import strawberry
import asyncio
from typing import AsyncGenerator
from api.graphql.types import AlertType, ServerType

# Globalny event bus — API wrzuca tu eventy, subskrypcje je odbierają
alert_events: asyncio.Queue = asyncio.Queue()
status_events: asyncio.Queue = asyncio.Queue()

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def alert_triggered(self) -> AsyncGenerator[AlertType, None]:
        """Subskrypcja alertów — dashboard dostaje nowe alerty na żywo."""
        while True:
            alert = await alert_events.get()
            yield alert

    @strawberry.subscription
    async def server_status_changed(self) -> AsyncGenerator[ServerType, None]:
        """Subskrypcja zmian statusu serwerów."""
        while True:
            server = await status_events.get()
            yield server
```

### Integracja z FastAPI

W `api/main.py` dodaj router GraphQL:

```python
from api.graphql.schema import graphql_router

# Dodaj obok istniejących endpointów REST:
app.include_router(graphql_router, prefix="/graphql")
```

## 2. Silnik alertów

Logika ewaluacji reguł. Wywoływana przy każdym heartbeatcie (z REST API):

```python
# api/graphql/alert_engine.py

from api.graphql.subscriptions import alert_events
from api.graphql.types import AlertType
from datetime import datetime

OPERATORS = {
    ">": lambda val, threshold: val > threshold,
    "<": lambda val, threshold: val < threshold,
    ">=": lambda val, threshold: val >= threshold,
    "<=": lambda val, threshold: val <= threshold,
    "==": lambda val, threshold: val == threshold,
    "!=": lambda val, threshold: val != threshold,
}

def evaluate_rules(server_id: str, cpu: float, mem: float, status: str, db):
    """Sprawdź wszystkie aktywne reguły dla danego heartbeata."""
    rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()

    metrics = {"cpu": cpu, "mem": mem, "status": 0 if status == "DOWN" else 1}

    for rule in rules:
        # Sprawdź czy reguła dotyczy tego serwera
        if rule.server_id and rule.server_id != server_id:
            continue

        value = metrics.get(rule.metric)
        if value is None:
            continue

        op_func = OPERATORS.get(rule.operator)
        if op_func and op_func(value, rule.threshold):
            # Reguła spełniona — utwórz alert
            alert = Alert(
                rule_name=rule.name,
                server_id=server_id,
                message=f"{rule.metric} {rule.operator} {rule.threshold} (actual: {value})",
            )
            db.add(alert)
            db.commit()

            # Emit do GraphQL Subscription
            alert_events.put_nowait(AlertType(
                id=alert.id,
                rule_name=rule.name,
                server_id=server_id,
                message=alert.message,
                timestamp=datetime.utcnow(),
            ))
```

## 3. Modele bazodanowe (dodaj do `api/models.py`)

Poproś Osobę 2 o dodanie tych modeli albo dodaj je sam:

```python
class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    metric: Mapped[str] = mapped_column(String(20))   # cpu, mem, status
    operator: Mapped[str] = mapped_column(String(5))   # >, <, ==, !=
    threshold: Mapped[float] = mapped_column(Float)
    server_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(200))
    server_id: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

## Jak testować

```bash
# Uruchom API
docker compose up api

# Otwórz GraphiQL playground:
# https://localhost:8080/graphql

# Przykładowe zapytanie:
query {
  servers {
    serverId
    status
    cpu
    mem
  }
}

# Utwórz regułę alertu:
mutation {
  createAlertRule(
    name: "Wysokie CPU"
    metric: "cpu"
    operator: ">"
    threshold: 80
  ) {
    id
    name
  }
}

# Subskrypcja (w GraphiQL lub z JS w przeglądarce):
subscription {
  alertTriggered {
    serverIdmessage
    timestamp
  }
}

# Test z przeglądarki (konsola F12):
# Subskrypcja GraphQL używa WebSocket automatycznie przez GraphiQL
```

## Pliki do edycji / utworzenia

```
api/graphql/
├── __init__.py
├── schema.py          # główny schemat + router
├── types.py           # typy GraphQL
├── queries.py         # zapytania
├── mutations.py       # mutacje (CRUD reguł alertów)
├── subscriptions.py   # subskrypcje (WebSocket)
└── alert_engine.py    # silnik ewaluacji reguł
```

## Dodatkowe zależności

Dodaj do `api/requirements.txt`:
```
strawberry-graphql[fastapi]
```
