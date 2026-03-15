# Przewodnik — Osoba 1: Warstwa TCP

## Co musisz zaimplementować

Dwa komponenty w Pythonie używające **czystych socketów** (moduł `socket` z biblioteki standardowej):

1. **Serwer TCP** (`tcp_server/server.py`) — odbiera heartbeaty od agentów i przekazuje dane do REST API
2. **Agent TCP** (`tcp_agent/agent.py`) — symuluje monitorowany serwer, wysyła heartbeaty co 10s

## Protokół komunikacji

Format wiadomości (tekst, rozdzielony `|`, zakończony `\n`):

```
Klient → Serwer:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>\n
Serwer → Klient:  ACK|<server_id>\n
```

Przykład:
```
Klient → Serwer:  HEARTBEAT|web-01|1710432000|45|72|OK\n
Serwer → Klient:  ACK|web-01\n
```

Pola:
| Pole | Typ | Opis |
|------|-----|------|
| `server_id` | string | Unikalny identyfikator serwera (np. `web-01`) |
| `timestamp` | int | Unix timestamp (sekundy) |
| `cpu` | int | Użycie CPU w % (0-100) |
| `mem` | int | Użycie RAM w % (0-100) |
| `status` | string | Zawsze `OK` (agent żyje) |

## Jak przekazać dane do REST API

Zamiast RabbitMQ — serwer TCP bezpośrednio wywołuje REST API po HTTPS.

```python
import requests
import json
import os
import urllib3

# Wyłącz ostrzeżenia o self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = os.environ.get("API_URL", "https://api:8080")

def send_heartbeat_to_api(data):
    """Wyślij heartbeat do REST API."""
    try:
        requests.post(
            f"{API_URL}/api/heartbeat",
            json=data,
            verify=False,  # self-signed cert
            timeout=5,
        )
    except requests.exceptions.RequestException as e:
        print(f"Error sending to API: {e}")

def send_status_change(server_id, status):
    """Zgłoś zmianę statusu (DOWN/UP) do REST API."""
    try:
        requests.post(
            f"{API_URL}/api/status",
            json={"server_id": server_id, "status": status},
            verify=False,
            timeout=5,
        )
    except requests.exceptions.RequestException as e:
        print(f"Error sending status to API: {e}")

# Przykład użycia po odebraniu heartbeata:
send_heartbeat_to_api({
    "server_id": "web-01",
    "cpu": 45,
    "mem": 72,
    "status": "OK",
    "timestamp": "2024-03-14T12:00:00"
})

# Przykład gdy serwer padł:
send_status_change("web-01", "DOWN")
```

## Logika wykrywania awarii

W serwerze TCP uruchom wątek (`threading.Thread`) który co 5 sekund sprawdza:
- Dla każdego `server_id` w `last_heartbeat`:
  - Jeśli `time.time() - last_heartbeat[server_id] > 30` → serwer nie żyje
  - Wywołaj `send_status_change(server_id, "DOWN")`
  - Gdy serwer wróci (pierwszy heartbeat po oznaczeniu DOWN) → `send_status_change(server_id, "UP")`

## Jak testować

```bash
# Uruchom swoją część + API
docker compose up api tcp-server tcp-agent

# Sprawdź logi
docker compose logs -f tcp-server

# Sprawdź czy heartbeaty dochodzą do API:
# Otwórz https://localhost:8080/docs → GET /api/servers
# Powinny pojawić się zarejestrowane serwery

# Skalowanie agentów
docker compose up --scale tcp-agent=3

# Symulacja awarii — zatrzymaj agenta
docker compose stop tcp-agent
# Po 30s serwer TCP powinien wysłać POST /api/status z DOWN
```

## Pliki do edycji

- `tcp_server/server.py` — uzupełnij `handle_client()` i `check_timeouts()`
- `tcp_agent/agent.py` — uzupełnij `main()`

## Dodatkowe zależności

Dodaj `requests` do `tcp_server/requirements.txt`:
```
requests
```

Szkielet kodu z komentarzami TODO jest już przygotowany. Wystarczy uzupełnić wskazane miejsca.
