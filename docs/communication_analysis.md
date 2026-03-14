# Analiza komunikacji

## Warstwy modelu TCP/IP

| Warstwa | Zastosowanie w projekcie |
|---------|--------------------------|
| **Aplikacji** | HTTP/REST (FastAPI), WebSocket, AMQP (RabbitMQ), własny protokół heartbeat |
| **Transportowa** | TCP — wszystkie połączenia (sockety, HTTP, WebSocket, AMQP) |
| **Internetowa** | IPv4 — sieć wewnętrzna Docker + localhost |
| **Dostępu do sieci** | Docker bridge network / Ethernet |

## Komunikacja stanowa vs bezstanowa

### Komunikacja stanowa (stateful)

| Połączenie | Opis |
|-----------|------|
| **TCP heartbeat** (Agent ↔ Serwer TCP) | Utrzymywane połączenie TCP — serwer śledzi stan każdego agenta (ostatni heartbeat, czy żyje). Zerwanie połączenia = potencjalna awaria. |
| **WebSocket** (Alert Worker ↔ Dashboard) | Utrzymywane połączenie dwukierunkowe. Serwer przechowuje listę podłączonych klientów i broadcastuje do nich alerty. |
| **AMQP** (Usługi ↔ RabbitMQ) | Kanały AMQP to stanowe połączenia — RabbitMQ śledzi konsumentów, kolejki i potwierdzenia dostarczenia. |

### Komunikacja bezstanowa (stateless)

| Połączenie | Opis |
|-----------|------|
| **HTTP REST API** | Każde żądanie HTTP jest niezależne — serwer nie przechowuje stanu między żądaniami. Klient wysyła pełne informacje w każdym requeście. |

## Porty i protokoły

| Port | Protokół | Usługa | Stanowy? | Warstwa |
|------|----------|--------|----------|---------|
| 9000 | TCP (własny protokół) | Serwer heartbeat | Tak | Transportowa + Aplikacji |
| 8080 | HTTPS (HTTP + TLS) | REST API | Nie | Aplikacji |
| 8765 | WebSocket (WS) | Serwer alertów | Tak | Aplikacji |
| 5672 | AMQP | RabbitMQ (broker) | Tak | Aplikacji |
| 15672 | HTTP | RabbitMQ panel zarządzania | Nie | Aplikacji |
| 3000 | HTTP | Dashboard (Nginx) | Nie | Aplikacji |

## Bezpieczeństwo

- REST API działa po **HTTPS** z certyfikatem self-signed (TLS/SSL)
- Szyfrowanie zapewnia poufność i integralność danych przesyłanych między dashboardem a API
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
