# Architektura systemu Watchdog

## Opis systemu

Watchdog to system monitorowania dostępności serwerów. Składa się z:
- **Agentów TCP** — zainstalowanych na monitorowanych serwerach, wysyłających cykliczne heartbeaty
- **Serwera TCP** — odbierającego heartbeaty i przekazującego dane do REST API
- **REST API (HTTPS)** — do zapisywania danych i zarządzania serwerami (FastAPI)
- **GraphQL API** — do elastycznych zapytań i subskrypcji real-time (Strawberry)
- **Silnika alertów** — ewaluacja reguł zdefiniowanych przez użytkownika (np. "CPU > 90%")
- **Dashboardu** — panel webowy z alertami na żywo

## Diagram architektury

```mermaid
graph TD
    subgraph "Monitorowane serwery"
        A1["Agent TCP #1<br/>klient socket"]y
        A2["Agent TCP #2<br/>klient socket"]
        A3["Agent TCP #N<br/>klient socket"]
    end

    subgraph "Serwer TCP :9000"
        TS["Serwer TCP<br/>Python socket<br/>— odbiera heartbeaty<br/>— wykrywa awarie<br/>— wywołuje REST API"]
    end

    subgraph "Backend :8080"
        API["FastAPI + HTTPS<br/>— REST API (zapis danych)<br/>— GraphQL (zapytania + subskrypcje)<br/>— silnik alertów"]
        GQL["Strawberry GraphQL<br/>— queries (serwery, historia, alerty)<br/>— mutations (reguły alertów)<br/>— subscriptions (WebSocket)"]
        DB[("SQLite<br/>servers / heartbeats<br/>incidents / alert_rules")]
    end

    subgraph "Frontend :3000"
        DASH["Dashboard<br/>HTML/JS<br/>— status serwerów<br/>— zarządzanie regułami alertów<br/>— alerty real-time"]
    end

    A1 -- "HEARTBEAT|id|ts|cpu|mem|status<br/>TCP :9000" --> TS
    A2 -- "TCP heartbeat" --> TS
    A3 -- "TCP heartbeat" --> TS
    TS -- "ACK|id" --> A1
    TS -- "ACK" --> A2
    TS -- "ACK" --> A3

    TS -- "POST /api/heartbeat<br/>HTTPS" --> API

    API --> DB
    API --> GQL
    GQL --> DB
    DASH -- "GraphQL query / mutation<br/>HTTPS" --> GQL
    DASH -. "GraphQL subscription<br/>WebSocket" .-> GQL

    style API fill:#1565c0,color:#fff
    style GQL fill:#6a1b9a,color:#fff
    style TS fill:#2e7d32,color:#fff
    style DASH fill:#37474f,color:#fff
    style DB fill:#1565c0,color:#fff
```

### Wymagania rozszerzające (zrealizowane 2 z min. 1)

| Wymaganie | Realizacja |
|-----------|-----------|
| **GraphQL** | Strawberry GraphQL — queries, mutations (reguły alertów), subscriptions |
| **WebSocket** | GraphQL Subscriptions — powiadomienia real-time o zmianach statusu i alertach |

## Użyte technologie

| Komponent | Technologia |
|-----------|-------------|
| Serwer/Agent TCP | Python, moduł `socket` |
| REST API | Python, FastAPI, SQLAlchemy |
| GraphQL | Strawberry GraphQL (integracja z FastAPI) |
| WebSocket | GraphQL Subscriptions (wbudowane w Strawberry) |
| Baza danych | SQLite |
| Dashboard | HTML/CSS/JavaScript |
| Konteneryzacja | Docker, Docker Compose |
| HTTPS | Certyfikat self-signed (OpenSSL) |

## Przepływ danych

1. **Agent TCP** wysyła heartbeat (`HEARTBEAT|server_id|timestamp|cpu|mem|status`) do **Serwera TCP** przez socket TCP
2. **Serwer TCP** odpowiada `ACK`, parsuje dane i wywołuje `POST /api/heartbeat` na **REST API** (HTTPS)
3. Jeśli agent nie wysyła heartbeata przez 30s → Serwer TCP wywołuje `POST /api/status` z `status=DOWN`
4. **REST API** zapisuje dane do **SQLite** i uruchamia **silnik alertów** — sprawdza reguły użytkownika
5. Jeśli reguła jest spełniona (np. CPU > 90%) → tworzony jest alert i emitowany przez **GraphQL Subscription** (WebSocket)
6. Przy każdym heartbeatcie i zmianie statusu → aktualizacja serwera pushowana przez **GraphQL Subscription** do dashboardu
7. **Dashboard** przy załadowaniu pobiera dane przez **GraphQL query** (HTTPS), potem wszystkie aktualizacje przychodzą przez **WebSocket** — bez pollingu
8. Użytkownik zarządza regułami alertów przez **GraphQL mutation** (HTTPS)

## Struktura projektu

| Folder | Opis |
|--------|------|
| `tcp_server/` | Serwer TCP — odbiera heartbeaty, wywołuje REST API |
| `tcp_agent/` | Klient TCP — symuluje monitorowane serwery |
| `api/` | REST API (FastAPI) + HTTPS + SQLite + modele bazodanowe |
| `api/graphql/` | GraphQL schema (Strawberry) — queries, mutations, subscriptions + silnik alertów |
| `dashboard/` | Panel webowy (GraphQL + WebSocket) |
| `docs/` | Dokumentacja architektury, analiza komunikacji |
