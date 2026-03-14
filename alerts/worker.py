"""
Alert Worker + WebSocket Server — Person 3

Consumes alert events (server.down, server.up) from RabbitMQ
and broadcasts them to connected WebSocket clients in real-time.

RabbitMQ:
  Exchange: monitor.events (topic)
  Queue: alert_queue
  Bindings: server.down, server.up, server.heartbeat

WebSocket message format (JSON):
  {"type": "alert",     "server_id": "web-01", "status": "DOWN", "timestamp": "..."}
  {"type": "recovery",  "server_id": "web-01", "status": "UP",   "timestamp": "..."}
  {"type": "heartbeat", "server_id": "web-01", "cpu": 45, "mem": 72, "timestamp": "..."}
"""

import os
import json
import asyncio
import threading
import pika
import websockets

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
WS_PORT = int(os.environ.get("WS_PORT", 8765))

# Connected WebSocket clients
connected_clients: set = set()


async def websocket_handler(websocket):
    """Handle a new WebSocket client connection."""
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)


async def broadcast(message: str):
    """Send a message to all connected WebSocket clients."""
    if connected_clients:
        await asyncio.gather(
            *[client.send(message) for client in connected_clients],
            return_exceptions=True,
        )


def setup_rabbitmq_consumer(loop: asyncio.AbstractEventLoop):
    """
    Connect to RabbitMQ, declare queue, and consume messages.
    Runs in a separate thread.
    """
    # TODO: Person 3 — implement RabbitMQ consumer
    #
    # 1. Connect to RabbitMQ (pika.BlockingConnection)
    # 2. Declare exchange: channel.exchange_declare(exchange="monitor.events", exchange_type="topic")
    # 3. Declare queue: channel.queue_declare(queue="alert_queue")
    # 4. Bind queue to routing keys:
    #    channel.queue_bind(exchange="monitor.events", queue="alert_queue", routing_key="server.down")
    #    channel.queue_bind(exchange="monitor.events", queue="alert_queue", routing_key="server.up")
    #    channel.queue_bind(exchange="monitor.events", queue="alert_queue", routing_key="server.heartbeat")
    # 5. Define callback that:
    #    a. Parses the JSON message body
    #    b. Determines type ("alert" for down, "recovery" for up, "heartbeat")
    #    c. Calls: asyncio.run_coroutine_threadsafe(broadcast(json.dumps(ws_message)), loop)
    # 6. Start consuming: channel.basic_consume(queue="alert_queue", on_message_callback=..., auto_ack=True)
    # 7. channel.start_consuming()
    pass


async def main():
    """Start WebSocket server and RabbitMQ consumer."""
    loop = asyncio.get_event_loop()

    # Start RabbitMQ consumer in background thread
    rabbit_thread = threading.Thread(
        target=setup_rabbitmq_consumer, args=(loop,), daemon=True
    )
    rabbit_thread.start()

    # Start WebSocket server
    async with websockets.serve(websocket_handler, "0.0.0.0", WS_PORT):
        print(f"WebSocket server running on port {WS_PORT}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
