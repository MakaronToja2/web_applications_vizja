"""
TCP Heartbeat Server — Person 1

Listens on TCP_PORT for heartbeat messages from agents.
Parses the custom protocol and publishes events to RabbitMQ.

Protocol format (text, pipe-delimited):
  Client -> Server:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>
  Server -> Client:  ACK|<server_id>

RabbitMQ exchange: monitor.events (topic)
  Routing keys: server.heartbeat, server.down, server.up
  Message body (JSON): {"server_id": "...", "cpu": 45, "mem": 72, "status": "OK", "timestamp": "..."}
"""

import socket
import threading
import json
import time
import os
import pika

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
TCP_PORT = int(os.environ.get("TCP_PORT", 9000))
HEARTBEAT_TIMEOUT = 30  # seconds before marking server as DOWN

# Track last heartbeat time per server_id
last_heartbeat: dict[str, float] = {}


def setup_rabbitmq():
    """Connect to RabbitMQ and declare the topic exchange."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()
    channel.exchange_declare(exchange="monitor.events", exchange_type="topic")
    return connection, channel


def publish_event(channel, routing_key: str, data: dict):
    """Publish a JSON event to the monitor.events exchange."""
    channel.basic_publish(
        exchange="monitor.events",
        routing_key=routing_key,
        body=json.dumps(data),
    )


def handle_client(conn: socket.socket, addr, channel):
    """Handle a single TCP client connection."""
    # TODO: Person 1 — implement protocol parsing
    #
    # 1. Receive data from conn (conn.recv(1024))
    # 2. Decode and split by '|'
    # 3. Validate message format
    # 4. Update last_heartbeat[server_id] = time.time()
    # 5. Publish to RabbitMQ: publish_event(channel, "server.heartbeat", {...})
    # 6. Send ACK back: conn.sendall(f"ACK|{server_id}\n".encode())
    # 7. Handle connection errors gracefully
    pass


def check_timeouts(channel):
    """Periodically check for servers that missed their heartbeat."""
    # TODO: Person 1 — implement timeout detection
    #
    # Run in a loop (e.g., every 5 seconds):
    # 1. For each server_id in last_heartbeat:
    #    if time.time() - last_heartbeat[server_id] > HEARTBEAT_TIMEOUT:
    #      publish_event(channel, "server.down", {"server_id": server_id, ...})
    #      remove from last_heartbeat (or mark as already notified)
    pass


def main():
    """Start the TCP server."""
    _, channel = setup_rabbitmq()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", TCP_PORT))
    server_socket.listen(5)
    print(f"TCP server listening on port {TCP_PORT}")

    # Start timeout checker in background thread
    timeout_thread = threading.Thread(target=check_timeouts, args=(channel,), daemon=True)
    timeout_thread.start()

    while True:
        conn, addr = server_socket.accept()
        print(f"Connection from {addr}")
        client_thread = threading.Thread(target=handle_client, args=(conn, addr, channel), daemon=True)
        client_thread.start()


if __name__ == "__main__":
    main()
