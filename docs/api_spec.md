# Specyfikacja REST API

Bazowy URL: `https://localhost:8080`

Interaktywna dokumentacja (Swagger): `https://localhost:8080/docs`

## Endpointy

### POST /api/servers
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

**Błędy:**
- `409` — serwer o tym `server_id` już istnieje

---

### GET /api/servers
Lista wszystkich zarejestrowanych serwerów z aktualnym statusem.

**Response (200):**
```json
[
    {
        "id": 1,
        "server_id": "web-01",
        "name": "Serwer webowy produkcyjny",
        "status": "UP",
        "last_heartbeat": "2024-03-14T12:05:00",
        "cpu": 45.0,
        "mem": 72.0,
        "created_at": "2024-03-14T12:00:00"
    }
]
```

---

### GET /api/servers/{server_id}
Szczegóły pojedynczego serwera.

**Response (200):** Jak wyżej (pojedynczy obiekt).

**Błędy:**
- `404` — nie znaleziono serwera

---

### DELETE /api/servers/{server_id}
Usunięcie serwera z monitorowania.

**Response:** `204 No Content`

**Błędy:**
- `404` — nie znaleziono serwera

---

### GET /api/servers/{server_id}/history?limit=100
Historia heartbeatów dla danego serwera.

**Parametry query:**
- `limit` (int, domyślnie 100) — maksymalna liczba wyników

**Response (200):**
```json
[
    {
        "id": 42,
        "server_id": "web-01",
        "cpu": 45.0,
        "mem": 72.0,
        "status": "OK",
        "timestamp": "2024-03-14T12:05:00"
    }
]
```

---

### GET /api/servers/{server_id}/incidents
Lista incydentów (awarii i przywróceń) dla serwera.

**Response (200):**
```json
[
    {
        "id": 1,
        "server_id": "web-01",
        "event_type": "DOWN",
        "timestamp": "2024-03-14T12:10:30"
    },
    {
        "id": 2,
        "server_id": "web-01",
        "event_type": "UP",
        "timestamp": "2024-03-14T12:11:00"
    }
]
```

---

### GET /api/stats
Zagregowane statystyki systemu.

**Response (200):**
```json
{
    "total_servers": 5,
    "servers_up": 3,
    "servers_down": 1,
    "servers_unknown": 1,
    "total_incidents": 12
}
```
