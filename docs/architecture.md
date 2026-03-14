# Architektura systemu Watchdog

## Opis systemu

Watchdog to system monitorowania dostępności serwerów. Składa się z:
- **Agentów TCP** — zainstalowanych na monitorowanych serwerach, wysyłających cykliczne heartbeaty
- **Serwera TCP** — odbierającego heartbeaty i wykrywającego awarie
- **Kolejki wiadomości (RabbitMQ)** — do asynchronicznej komunikacji między usługami
- **REST API (HTTPS)** — do zarządzania serwerami i przeglądania danych
- **Serwera WebSocket** — do powiadomień w czasie rzeczywistym
- **Dashboardu** — panelu webowego wyświetlającego status serwerów i alerty

## Diagram architektury

```mermaid
graph TD
    subgraph Monitorowane serwery
        A1[Agent TCP #1<br/>klient socket]
        A2[Agent TCP #2<br/>klient socket]
        A3[Agent TCP #N<br/>klient socket]
    end

    subgraph "Serwer TCP :9000"
        TS[Serwer TCP<br/>Python socket<br/>— odbiera heartbeaty<br/>— wykrywa awarie]
    end

    subgraph "Message Broker :5672"
        RMQ[RabbitMQ<br/>Exchange: monitor.events<br/>topic exchange]
    end

    subgraph "REST API :8080"
        API[FastAPI + HTTPS<br/>— CRUD serwerów<br/>— historia heartbeatów<br/>— statystyki]
        DB[(SQLite<br/>servers / heartbeats / incidents)]
    end

    subgraph "Alert Worker :8765"
        AW[Konsumer RabbitMQ<br/>+ Serwer WebSocket<br/>— przetwarza alerty<br/>— broadcast do klientów]
    end

    subgraph "Frontend :3000"
        DASH[Dashboard<br/>Nginx + HTML/JS<br/>— lista serwerów<br/>— alerty real-time]
    end

    A1 -- "HEARTBEAT|id|ts|cpu|mem|status<br/>TCP :9000" --> TS
    A2 -- "TCP heartbeat" --> TS
    A3 -- "TCP heartbeat" --> TS
    TS -- "ACK|id" --> A1
    TS -- "ACK" --> A2
    TS -- "ACK" --> A3

    TS -- "server.heartbeat<br/>server.down<br/>server.up<br/>AMQP" --> RMQ

    RMQ -- "api_heartbeat_queue<br/>server.heartbeat / .down / .up" --> API
    RMQ -- "alert_queue<br/>server.down / .up / .heartbeat" --> AW

    API --> DB
    API -- "HTTPS GET/POST<br/>JSON" --> DASH
    AW -- "WebSocket ws://<br/>JSON alerts" --> DASH

    style RMQ fill:#ff6d00,color:#fff
    style API fill:#1565c0,color:#fff
    style AW fill:#6a1b9a,color:#fff
    style TS fill:#2e7d32,color:#fff
    style DASH fill:#37474f,color:#fff
    style DB fill:#1565c0,color:#fff
```

### Wymagania rozszerzające (zrealizowane 2 z min. 1)

| Wymaganie | Realizacja |
|-----------|-----------|
| **Message Queue** | RabbitMQ — asynchroniczna komunikacja między Serwerem TCP, REST API i Alert Workerem |
| **WebSocket** | Serwer WebSocket w Alert Worker — powiadomienia real-time do dashboardu |

## Użyte technologie

| Komponent | Technologia |
|-----------|-------------|
| Serwer/Agent TCP | Python, moduł `socket` |
| REST API | Python, FastAPI, SQLAlchemy |
| Baza danych | SQLite |
| Kolejka wiadomości | RabbitMQ (AMQP) |
| WebSocket | Python, biblioteka `websockets` |
| Dashboard | HTML/CSS/JavaScript |
| Konteneryzacja | Docker, Docker Compose |
| HTTPS | Certyfikat self-signed (OpenSSL) |

## Przepływ danych

1. **Agent TCP** wysyła heartbeat (`HEARTBEAT|server_id|timestamp|cpu|mem|status`) do **Serwera TCP** przez socket TCP
2. **Serwer TCP** odpowiada `ACK`, parsuje dane i publikuje zdarzenie `server.heartbeat` do **RabbitMQ**
3. Jeśli agent nie wysyła heartbeata przez 30s → Serwer TCP publikuje `server.down`
4. **REST API** konsumuje zdarzenia z RabbitMQ i zapisuje je do **SQLite**
5. **Alert Worker** konsumuje zdarzenia `server.down`/`server.up` i broadcastuje je przez **WebSocket**
6. **Dashboard** pobiera listę serwerów z REST API (HTTPS) i odbiera alerty na żywo przez WebSocket
