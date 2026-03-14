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
| REST API (HTTPS) | 8443 | https://localhost:8443/docs |
| Serwer TCP (heartbeat) | 9000 | — |
| WebSocket (alerty) | 8765 | ws://localhost:8765 |
| Dashboard | 3000 | http://localhost:3000 |
| RabbitMQ Panel | 15672 | http://localhost:15672 (guest/guest) |

## Struktura projektu

| Folder | Osoba | Opis |
|--------|-------|------|
| `tcp_server/` | Osoba 1 | Serwer TCP — odbiera heartbeaty (sockety) |
| `tcp_agent/` | Osoba 1 | Klient TCP — symuluje monitorowane serwery |
| `api/` | Osoba 2 | REST API + HTTPS (FastAPI) |
| `alerts/` | Osoba 3 | Konsumer RabbitMQ + serwer WebSocket |
| `dashboard/` | Wspólne | Prosty panel webowy |
| `docs/` | Wspólne | Dokumentacja architektury |

## Testowanie poszczególnych komponentów

```bash
# Tylko RabbitMQ + warstwa TCP
docker compose up rabbitmq tcp-server tcp-agent

# Tylko RabbitMQ + API
docker compose up rabbitmq api

# Tylko RabbitMQ + alerty
docker compose up rabbitmq alert-worker

# Skalowanie agentów (symulacja wielu serwerów)
docker compose up --scale tcp-agent=5
```
