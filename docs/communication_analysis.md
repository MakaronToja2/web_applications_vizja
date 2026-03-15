# Analiza komunikacji

## Warstwy modelu TCP/IP

| Warstwa | Zastosowanie w projekcie |
|---------|--------------------------|
| **Aplikacji** | HTTP/REST (FastAPI), GraphQL (Strawberry), WebSocket (GraphQL Subscriptions), własny protokół heartbeat |
| **Transportowa** | TCP — wszystkie połączenia (sockety, HTTP, WebSocket) |
| **Internetowa** | IPv4 — sieć wewnętrzna Docker + localhost |
| **Dostępu do sieci** | Docker bridge network / Ethernet |

## Komunikacja stanowa vs bezstanowa

### Komunikacja stanowa (stateful)

| Połączenie | Opis |
|-----------|------|
| **TCP heartbeat** (Agent ↔ Serwer TCP) | Utrzymywane połączenie TCP — serwer śledzi stan każdego agenta (ostatni heartbeat, czy żyje). Zerwanie połączenia = potencjalna awaria. |
| **GraphQL Subscription** (API ↔ Dashboard) | Utrzymywane połączenie WebSocket — serwer pushuje do dashboardu: aktualizacje metryk (CPU/RAM) przy każdym heartbeatcie, zmiany statusu (UP/DOWN), nowe alerty. Dashboard nie używa pollingu — wszystkie dane na żywo przychodzą przez WebSocket. |

### Komunikacja bezstanowa (stateless)

| Połączenie | Opis |
|-----------|------|
| **HTTP REST API** (Serwer TCP → API) | Każde żądanie HTTP jest niezależne — serwer TCP wywołuje `POST /api/heartbeat` per heartbeat. |
| **GraphQL Query/Mutation** (Dashboard → API) | Pojedyncze zapytania HTTPS — każde niezależne. Używane przy załadowaniu strony (inicjalne pobranie danych) oraz do operacji zapisu (tworzenie/usuwanie reguł alertów, usuwanie serwerów). Po załadowaniu strony dalsze aktualizacje przychodzą przez WebSocket. |

## Porty i protokoły

| Port | Protokół | Usługa | Stanowy? | Warstwa |
|------|----------|--------|----------|---------|
| 9000 | TCP (własny protokół) | Serwer heartbeat | Tak | Transportowa + Aplikacji |
| 8080 | HTTPS (HTTP + TLS) | REST API + GraphQL | Nie (query/mutation) / Tak (subscription) | Aplikacji |
| 8080 | WebSocket (WSS) | GraphQL Subscriptions | Tak | Aplikacji |
| 3000 | HTTP | Dashboard (Nginx) | Nie | Aplikacji |

## Bezpieczeństwo

- REST API i GraphQL działają po **HTTPS** z certyfikatem self-signed (TLS/SSL)
- GraphQL Subscriptions używają **WSS** (WebSocket Secure) — ten sam certyfikat
- Szyfrowanie zapewnia poufność i integralność danych przesyłanych między dashboardem a API
- Komunikacja Serwer TCP → API również po HTTPS (wewnątrz sieci Docker)
- Certyfikat generowany poleceniem:
  ```bash
  openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
  ```

## Opis własnego protokołu TCP

### Format wiadomości

```
Klient → Serwer:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>\n
Serwer → Klient:  ACK|<server_id>\n
```

### Pola

| Pole | Typ | Opis |
|------|-----|------|
| `server_id` | string | Unikalny identyfikator monitorowanego serwera |
| `timestamp` | int | Czas wysłania (Unix timestamp) |
| `cpu` | int | Użycie procesora (0-100%) |
| `mem` | int | Użycie pamięci RAM (0-100%) |
| `status` | string | Status agenta (`OK`) |

### Cykl życia połączenia

1. Agent nawiązuje połączenie TCP z serwerem (3-way handshake)
2. Agent wysyła heartbeat co 10 sekund
3. Serwer odpowiada ACK po każdym heartbeatcie
4. Jeśli serwer nie otrzyma heartbeata przez 30s → oznacza serwer jako DOWN
5. Połączenie utrzymywane do momentu zamknięcia agenta lub awarii sieci

## GraphQL vs REST — dlaczego oba?

| | REST API | GraphQL |
|---|---|---|
| **Kto używa** | Serwer TCP (wewnętrzne wywołania) | Dashboard (frontend) |
| **Do czego** | Prosty zapis danych: `POST /api/heartbeat`, `POST /api/status` | Elastyczne zapytania, zarządzanie regułami alertów, subskrypcje real-time |
| **Dlaczego** | Serwer TCP nie potrzebuje elastyczności — zawsze wysyła te same dane | Dashboard potrzebuje różnych widoków + real-time push (subscriptions) |
| **Typ komunikacji** | Bezstanowa (request-response) | Bezstanowa (query/mutation) + Stanowa (subscription/WebSocket) |
