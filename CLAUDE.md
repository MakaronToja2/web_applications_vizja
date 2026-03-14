# CLAUDE.md

## Projekt

**Watchdog** — system monitorowania dostępności serwerów. Projekt zaliczeniowy z przedmiotu "Programowanie aplikacji sieciowych" (3 osoby).

## Architektura

```
TCP Agent → TCP Server → RabbitMQ → { REST API (FastAPI), Alert Worker (WebSocket) } → Dashboard
```

- **Serwer TCP** (port 9000) — odbiera heartbeaty od agentów, publikuje zdarzenia do RabbitMQ
- **REST API** (port 8080, HTTPS) — CRUD serwerów, historia, statystyki (FastAPI + SQLite)
- **Alert Worker** (port 8765) — konsumuje zdarzenia z RabbitMQ, broadcastuje przez WebSocket
- **Dashboard** (port 3000) — panel webowy (Nginx + statyczny HTML/JS)
- **RabbitMQ** (port 5672/15672) — broker wiadomości, exchange `monitor.events` (topic)

## Podział ról

| Folder | Osoba | Opis |
|--------|-------|------|
| `tcp_server/`, `tcp_agent/` | Osoba 1 | Serwer i klient TCP (sockety), publikacja do RabbitMQ |
| `api/` | Osoba 2 | REST API (FastAPI) + HTTPS + konsumer RabbitMQ → SQLite |
| `alerts/` | Osoba 3 | Konsumer RabbitMQ + serwer WebSocket |
| `dashboard/` | Wspólne | Panel webowy |
| `docs/` | Wspólne | Dokumentacja |

## Uruchamianie

```bash
# Wygeneruj certyfikat (jednorazowo)
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=localhost"

# Zbuduj i uruchom
docker compose build
docker compose up
```

## Komendy developerskie

```bash
docker compose up rabbitmq tcp-server tcp-agent   # tylko TCP
docker compose up rabbitmq api                     # tylko API
docker compose up rabbitmq alert-worker            # tylko alerty
docker compose logs -f <service>                   # logi
```

## Konwencje

- **Język dokumentacji:** polski (README, docs/, komentarze w markdown)
- **Język kodu:** angielski (nazwy zmiennych, komentarze w kodzie, docstringi)
- **Stack:** Python 3.12, FastAPI, pika (RabbitMQ), websockets, SQLAlchemy, SQLite
- **Konteneryzacja:** Docker — każdy serwis ma swój Dockerfile, wspólny docker-compose.yml

## Protokół TCP (własny)

```
Klient → Serwer:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>\n
Serwer → Klient:  ACK|<server_id>\n
```

## RabbitMQ

- Exchange: `monitor.events` (topic)
- Routing keys: `server.heartbeat`, `server.down`, `server.up`
- Kolejki: `api_heartbeat_queue` (API), `alert_queue` (Alert Worker)
- Body: JSON, np. `{"server_id": "web-01", "cpu": 45, "mem": 72, "status": "OK", "timestamp": "..."}`

## Pliki z TODO dla kolegów

Pliki `tcp_server/server.py`, `tcp_agent/agent.py` i `alerts/worker.py` mają gotowy szkielet z komentarzami `# TODO:` wskazującymi co trzeba uzupełnić. Przewodniki w `docs/person1_guide.md` i `docs/person3_guide.md`.

## Ważne

- API (folder `api/`) jest w pełni zaimplementowane — nie trzeba go ruszać
- Dashboard (`dashboard/`) jest gotowy — pobiera dane z API i łączy się z WebSocket
- Nie commitować folderu `certs/` (jest w .gitignore)
