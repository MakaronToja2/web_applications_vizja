# Przewodnik — Osoba 1: Warstwa TCP

## Co musisz zaimplementować

Dwa komponenty w Pythonie używające **czystych socketów** (moduł `socket` z biblioteki standardowej):

1. **Serwer TCP** (`tcp_server/server.py`) — odbiera heartbeaty od agentów i publikuje zdarzenia do RabbitMQ
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

## Format wiadomości RabbitMQ

Serwer TCP po odebraniu heartbeata publikuje do RabbitMQ:

- **Exchange:** `monitor.events` (typ: `topic`)
- **Routing key:** `server.heartbeat`, `server.down`, lub `server.up`
- **Body (JSON):**

```json
{
    "server_id": "web-01",
    "cpu": 45,
    "mem": 72,
    "status": "OK",
    "timestamp": "2024-03-14T12:00:00"
}
```

Dla zdarzeń `server.down` / `server.up`:
```json
{
    "server_id": "web-01",
    "status": "DOWN",
    "timestamp": "2024-03-14T12:00:30"
}
```

## Jak połączyć się z RabbitMQ (pika)

```python
import pika
import json
import os

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST)
)
channel = connection.channel()
channel.exchange_declare(exchange="monitor.events", exchange_type="topic")

# Publikacja zdarzenia
def publish_event(routing_key, data):
    channel.basic_publish(
        exchange="monitor.events",
        routing_key=routing_key,
        body=json.dumps(data),
    )

# Przykład użycia
publish_event("server.heartbeat", {
    "server_id": "web-01",
    "cpu": 45,
    "mem": 72,
    "status": "OK",
    "timestamp": "2024-03-14T12:00:00"
})
```

## Logika wykrywania awarii

W serwerze TCP uruchom wątek (`threading.Thread`) który co 5 sekund sprawdza:
- Dla każdego `server_id` w `last_heartbeat`:
  - Jeśli `time.time() - last_heartbeat[server_id] > 30` → serwer nie żyje
  - Opublikuj `server.down` do RabbitMQ
  - Gdy serwer wróci (pierwszy heartbeat po oznaczeniu DOWN) → opublikuj `server.up`

## Jak testować

```bash
# Uruchom tylko swoją część + RabbitMQ
docker-compose up rabbitmq tcp-server tcp-agent

# Sprawdź logi
docker-compose logs -f tcp-server

# Panel RabbitMQ — sprawdź czy wiadomości docierają
# http://localhost:15672 (login: guest / hasło: guest)
# Zakładka "Exchanges" → monitor.events → powinny być wiadomości

# Skalowanie agentów
docker-compose up --scale tcp-agent=3

# Symulacja awarii — zatrzymaj agenta
docker-compose stop tcp-agent
# Po 30s serwer powinien opublikować server.down
```

## Pliki do edycji

- `tcp_server/server.py` — uzupełnij funkcje `handle_client()` i `check_timeouts()`
- `tcp_agent/agent.py` — uzupełnij funkcję `main()`

Szkielet kodu z komentarzami TODO jest już przygotowany. Wystarczy uzupełnić wskazane miejsca.
