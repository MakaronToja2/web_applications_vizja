# Watchdog — System Monitorowania Serwerów

## Szybki start

```bash
# 1. Wygeneruj certyfikat self-signed (jednorazowo)
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=localhost"

# 2. Zbuduj i uruchom
docker compose build
docker compose up
```

## Usługi

| Usługa | Port | URL |
|--------|------|-----|
| REST API + GraphQL (HTTPS) | 8080 | https://localhost:8080/docs |
| GraphQL Playground | 8080 | https://localhost:8080/graphql |
| Serwer TCP (heartbeat) | 9000 | — |
| Dashboard | 3000 | http://localhost:3000 |

## Struktura projektu

| Folder | Opis |
|--------|------|
| `tcp_server/` | Serwer TCP — odbiera heartbeaty (sockety) |
| `tcp_agent/` | Klient TCP — symuluje monitorowane serwery |
| `api/` | REST API + HTTPS (FastAPI) + baza danych |
| `api/graphql/` | GraphQL schema + silnik alertów (Strawberry) |
| `dashboard/` | Panel webowy (GraphQL + WebSocket) |
| `docs/` | Dokumentacja architektury |

## Testowanie poszczególnych komponentów

```bash
# API + TCP
docker compose up api tcp-server tcp-agent

# Tylko API (z GraphQL playground)
docker compose up api

# Skalowanie agentów (symulacja wielu serwerów)
docker compose up --scale tcp-agent=5
```
