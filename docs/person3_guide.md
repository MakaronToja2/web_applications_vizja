# Przewodnik — Osoba 3: RabbitMQ + WebSocket

## Co musisz zaimplementować

Jeden komponent w Pythonie (`alerts/worker.py`) który:

1. **Konsumuje wiadomości z RabbitMQ** — odbiera zdarzenia `server.down`, `server.up` i `server.heartbeat`
2. **Serwer WebSocket** — wysyła alerty w czasie rzeczywistym do podłączonych klientów (dashboard w przeglądarce)

## Architektura

```
RabbitMQ (monitor.events)
    │
    │  server.down / server.up / server.heartbeat
    ▼
Alert Worker (worker.py)
    │
    │  broadcast JSON via WebSocket
    ▼
Dashboard (przeglądarka)
```

## Konfiguracja RabbitMQ

### Exchange i kolejki

```python
import pika
import os

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST)
)
channel = connection.channel()

# Deklaracja exchange (ten sam co w serwerze TCP)
channel.exchange_declare(exchange="monitor.events", exchange_type="topic")

# Twoja kolejka
channel.queue_declare(queue="alert_queue")

# Bindowanie — jakie wiadomości chcesz odbierać
channel.queue_bind(exchange="monitor.events", queue="alert_queue", routing_key="server.down")
channel.queue_bind(exchange="monitor.events", queue="alert_queue", routing_key="server.up")
channel.queue_bind(exchange="monitor.events", queue="alert_queue", routing_key="server.heartbeat")
```

## Format wiadomości przychodzących (z RabbitMQ)

```json
// routing_key: server.heartbeat
{"server_id": "web-01", "cpu": 45, "mem": 72, "status": "OK", "timestamp": "..."}

// routing_key: server.down
{"server_id": "web-01", "status": "DOWN", "timestamp": "..."}

// routing_key: server.up
{"server_id": "web-01", "status": "UP", "timestamp": "..."}
```

## Format wiadomości wychodzących (WebSocket → Dashboard)

Przetłumacz wiadomość z RabbitMQ na format WebSocket:

```json
// Gdy server.down
{"type": "alert", "server_id": "web-01", "status": "DOWN", "timestamp": "..."}

// Gdy server.up
{"type": "recovery", "server_id": "web-01", "status": "UP", "timestamp": "..."}

// Gdy server.heartbeat
{"type": "heartbeat", "server_id": "web-01", "cpu": 45, "mem": 72, "timestamp": "..."}
```

## Jak łączyć RabbitMQ (wątek) z WebSocket (asyncio)

RabbitMQ (`pika`) jest synchroniczny, WebSocket (`websockets`) jest asynchroniczny.
Rozwiązanie: RabbitMQ działa w osobnym wątku i używa `asyncio.run_coroutine_threadsafe()` do wysyłki.

```python
import asyncio
import threading

# Z wątku RabbitMQ wysyłasz do asyncio:
def on_rabbitmq_message(ch, method, properties, body):
    data = json.loads(body)
    ws_message = transform_to_ws_format(data, method.routing_key)
    # Wyślij do pętli asyncio
    asyncio.run_coroutine_threadsafe(
        broadcast(json.dumps(ws_message)),
        event_loop  # referencja do pętli asyncio
    )
```

## Jak testować

```bash
# Uruchom swoją część + RabbitMQ
docker-compose up rabbitmq alert-worker

# Sprawdź logi
docker-compose logs -f alert-worker

# Test ręczny — opublikuj wiadomość do RabbitMQ:
# 1. Otwórz http://localhost:15672 (guest/guest)
# 2. Zakładka "Exchanges" → monitor.events
# 3. "Publish message":
#    Routing key: server.down
#    Payload: {"server_id": "test-01", "status": "DOWN", "timestamp": "2024-01-01T00:00:00"}

# Test WebSocket z przeglądarki (konsola F12):
# ws = new WebSocket("ws://localhost:8765")
# ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

## Pliki do edycji

- `alerts/worker.py` — uzupełnij funkcję `setup_rabbitmq_consumer()`

Szkielet kodu z komentarzami TODO jest już przygotowany. Wystarczy uzupełnić wskazane miejsca.
