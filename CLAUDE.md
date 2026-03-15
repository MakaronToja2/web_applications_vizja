# CLAUDE.md

## Projekt

**Watchdog** — system monitorowania dostępności serwerów. Projekt zaliczeniowy z przedmiotu "Programowanie aplikacji sieciowych" (3 osoby).

## Architektura

```
TCP Agent → TCP Server → REST API (FastAPI + HTTPS) → SQLite
                                    ↕
Dashboard ← GraphQL queries + GraphQL Subscriptions (WebSocket)
```

- **Serwer TCP** (port 9000) — odbiera heartbeaty od agentów, wywołuje REST API
- **REST API + GraphQL** (port 8080, HTTPS) — CRUD serwerów, GraphQL queries/mutations/subscriptions, silnik alertów (FastAPI + Strawberry)
- **Dashboard** (port 3000) — panel webowy (Nginx + statyczny HTML/JS)

## Struktura

| Folder | Opis |
|--------|------|
| `tcp_server/`, `tcp_agent/` | Serwer i klient TCP (sockety), wywołania REST API |
| `api/` | REST API (FastAPI) + HTTPS + SQLite + modele bazodanowe |
| `api/graphql/` | GraphQL schema (Strawberry) — queries, mutations, subscriptions + silnik alertów |
| `dashboard/` | Panel webowy (GraphQL + WebSocket) |
| `docs/` | Dokumentacja architektury |

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
docker compose up api tcp-server tcp-agent   # TCP + API
docker compose up api                         # tylko API
docker compose logs -f <service>              # logi
```

## Konwencje

- **Język dokumentacji:** polski (README, docs/, komentarze w markdown)
- **Język kodu:** angielski (nazwy zmiennych, komentarze w kodzie, docstringi)
- **Stack:** Python 3.12, FastAPI, Strawberry GraphQL, SQLAlchemy, SQLite
- **Konteneryzacja:** Docker — każdy serwis ma swój Dockerfile, wspólny docker-compose.yml

## Protokół TCP (własny)

```
Klient → Serwer:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>\n
Serwer → Klient:  ACK|<server_id>\n
```

## GraphQL

- Endpoint: `/graphql` (HTTPS)
- Playground: `https://localhost:8080/graphql` (GraphiQL)
- Queries: `servers`, `server(id)`, `alertRules`, `alerts`, `stats`
- Mutations: `createAlertRule`, `deleteAlertRule`, `toggleAlertRule`
- Subscriptions: `alertTriggered`, `serverStatusChanged` — real-time przez WebSocket

## Silnik alertów

Użytkownik definiuje reguły (np. "CPU > 90%", "status == DOWN"). Przy każdym heartbeatcie reguły są ewaluowane. Jeśli spełnione → alert zapisany w DB + push przez GraphQL Subscription.

## Pliki z TODO dla kolegów

- `tcp_server/server.py`, `tcp_agent/agent.py` — szkielet z TODO dla Osoby 1
- `api/graphql/` — przewodnik w `docs/person3_guide.md` dla Osoby 3

## Ważne

- API (folder `api/`) — endpointy REST są zaimplementowane
- Warstwa GraphQL (`api/graphql/`) i dashboard do zaimplementowania
- Nie ma RabbitMQ — Serwer TCP komunikuje się z API bezpośrednio przez HTTPS
- Nie commitować folderu `certs/` (jest w .gitignore)
