# Specyfikacja API

## REST API

Bazowy URL: `https://localhost:8080`

Interaktywna dokumentacja (Swagger): `https://localhost:8080/docs`

### Endpointy REST (używane przez Serwer TCP)

#### POST /api/heartbeat
Odbiór heartbeata z serwera TCP.

**Request:**
```json
{
    "server_id": "web-01",
    "cpu": 45,
    "mem": 72,
    "status": "OK",
    "timestamp": "2024-03-14T12:00:00"
}
```

**Response (200):**
```json
{"ok": true}
```

---

#### POST /api/status
Zmiana statusu serwera (UP/DOWN) — wywoływane przez serwer TCP przy wykryciu awarii.

**Request:**
```json
{
    "server_id": "web-01",
    "status": "DOWN"
}
```

**Response (200):**
```json
{"ok": true}
```

---

#### POST /api/servers
Rejestracja nowego serwera do monitorowania.

**Request:**
```json
{
    "server_id": "web-01",
    "name": "Serwer webowy produkcyjny"
}
```

**Response (201):**
```json
{
    "id": 1,
    "server_id": "web-01",
    "name": "Serwer webowy produkcyjny",
    "status": "UNKNOWN",
    "last_heartbeat": null,
    "cpu": null,
    "mem": null,
    "created_at": "2024-03-14T12:00:00"
}
```

---

#### GET /api/servers
Lista wszystkich zarejestrowanych serwerów z aktualnym statusem.

---

#### GET /api/servers/{server_id}
Szczegóły pojedynczego serwera.

---

#### DELETE /api/servers/{server_id}
Usunięcie serwera z monitorowania. **Response:** `204 No Content`

---

## GraphQL API

Endpoint: `https://localhost:8080/graphql`

Playground (GraphiQL): `https://localhost:8080/graphql`

### Queries

```graphql
# Lista serwerów
query {
  servers {
    serverId
    name
    status
    cpu
    mem
    lastHeartbeat
  }
}

# Pojedynczy serwer
query {
  server(serverId: "web-01") {
    serverId
    status
    cpu
    mem
  }
}

# Reguły alertów
query {
  alertRules {
    id
    name
    metric
    operator
    threshold
    enabled
  }
}

# Ostatnie alerty
query {
  alerts(limit: 20) {
    id
    ruleName
    serverId
    message
    timestamp
  }
}

# Statystyki
query {
  stats {
    totalServers
    serversUp
    serversDown
    totalAlerts
  }
}
```

### Mutations

```graphql
# Utwórz regułę alertu
mutation {
  createAlertRule(
    name: "Wysokie CPU"
    metric: "cpu"
    operator: ">"
    threshold: 90
  ) {
    id
    name
  }
}

# Utwórz regułę dla konkretnego serwera
mutation {
  createAlertRule(
    name: "Web-01 RAM"
    metric: "mem"
    operator: ">"
    threshold: 85
    serverId: "web-01"
  ) {
    id
  }
}

# Usuń regułę
mutation {
  deleteAlertRule(id: 1)
}

# Włącz/wyłącz regułę
mutation {
  toggleAlertRule(id: 1, enabled: false) {
    id
    enabled
  }
}
```

### Subscriptions (WebSocket)

```graphql
# Alerty w czasie rzeczywistym
subscription {
  alertTriggered {
    serverId
    ruleName
    message
    timestamp
  }
}

# Zmiany statusu serwerów
subscription {
  serverStatusChanged {
    serverId
    status
    cpu
    mem
  }
}
```
