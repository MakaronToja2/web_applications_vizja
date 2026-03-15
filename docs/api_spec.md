# Specyfikacja API

## REST API (komunikacja wewnętrzna: Serwer TCP → API)

Bazowy URL: `https://localhost:8080`

Interaktywna dokumentacja (Swagger): `https://localhost:8080/docs`

REST API służy wyłącznie do **zapisu danych** przez Serwer TCP. Nie udostępnia operacji odczytu — te realizowane są przez GraphQL.

### POST /api/heartbeat
Odbiór heartbeata z serwera TCP. Jeśli serwer o danym `server_id` nie istnieje — zostanie automatycznie zarejestrowany.

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

**Efekty uboczne:**
- Upsert serwera w bazie danych (status → UP, aktualizacja CPU/RAM)
- Zapis heartbeata do historii
- Ewaluacja reguł alertów → jeśli reguła spełniona → alert + push przez WebSocket

---

### POST /api/status
Zmiana statusu serwera (DOWN/UP) — wywoływane przez serwer TCP przy wykryciu awarii lub powrocie serwera.

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

**Efekty uboczne:**
- Aktualizacja statusu serwera w bazie
- Zapis incydentu (DOWN/UP) do historii
- Ewaluacja reguł alertów → push przez WebSocket

---

## GraphQL API (komunikacja z dashboardem)

Endpoint: `https://localhost:8080/graphql`

Playground (GraphiQL): `https://localhost:8080/graphql`

GraphQL obsługuje **wszystkie operacje odczytu i zapisu** dla dashboardu — zapytania o serwery, zarządzanie regułami alertów, oraz subskrypcje real-time.

### Queries (odczyt danych)

```graphql
# Lista serwerów
{
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
{
  server(serverId: "web-01") {
    serverId
    status
    cpu
    mem
  }
}

# Reguły alertów
{
  alertRules {
    id
    name
    metric
    operator
    threshold
    serverId
    enabled
  }
}

# Ostatnie alerty
{
  alerts(limit: 20) {
    id
    ruleName
    serverId
    message
    timestamp
  }
}

# Statystyki
{
  stats {
    totalServers
    serversUp
    serversDown
    totalAlerts
  }
}
```

### Mutations (zapis danych)

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

# Usuń serwer (wraz z historią heartbeatów, incydentów i alertów)
mutation {
  deleteServer(serverId: "web-01")
}

# Wyczyść wszystkie alerty (zwraca liczbę usuniętych)
mutation {
  clearAlerts
}
```

### Subscriptions (WebSocket — real-time)

Subskrypcje utrzymują połączenie WebSocket (WSS) i pushują eventy do klienta w momencie ich wystąpienia.

```graphql
# Alerty w czasie rzeczywistym — fires gdy reguła alertu zostanie spełniona
subscription {
  alertTriggered {
    id
    serverId
    ruleName
    message
    timestamp
  }
}

# Zmiany statusu serwerów — fires gdy serwer zmieni status (UP/DOWN)
subscription {
  serverStatusChanged {
    serverId
    status
    cpu
    mem
  }
}
```

## Dlaczego REST + GraphQL?

| | REST API | GraphQL |
|---|---|---|
| **Kto używa** | Serwer TCP (wewnętrzne wywołania) | Dashboard (frontend) |
| **Do czego** | Zapis danych: heartbeaty, zmiany statusu | Odczyt danych, zarządzanie regułami, subskrypcje |
| **Dlaczego** | Prosty `POST` — serwer TCP nie potrzebuje elastyczności | Dashboard potrzebuje elastycznych zapytań + push real-time |
| **Typ** | Bezstanowy (request-response) | Bezstanowy (query/mutation) + Stanowy (subscription/WebSocket) |
