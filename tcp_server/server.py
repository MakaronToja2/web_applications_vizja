"""
TCP Heartbeat Server

Listens on TCP_PORT for heartbeat messages from agents.
Parses the custom protocol and forwards data to the REST API via HTTPS.

Protocol format (text, pipe-delimited):
  Client -> Server:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>
  Server -> Client:  ACK|<server_id>

API endpoints called:
  POST /api/heartbeat  — forward heartbeat data
  POST /api/status     — report status change (DOWN/UP)
"""

import socket
import threading
import time
import os
from datetime import datetime
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = os.environ.get("API_URL", "https://localhost:8080")
TCP_PORT = int(os.environ.get("TCP_PORT", 9000))
HEARTBEAT_TIMEOUT = 30

# Track last heartbeat time per server_id
last_heartbeat: dict[str, float] = {}
servers_down: set[str] = set()
lock = threading.Lock()


def send_heartbeat_to_api(data: dict):
    """Forward heartbeat data to REST API."""
    try:
        requests.post(f"{API_URL}/api/heartbeat", json=data, verify=False, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"Error sending heartbeat to API: {e}")


def send_status_change(server_id: str, status: str):
    """Report a status change (DOWN/UP) to REST API."""
    try:
        requests.post(
            f"{API_URL}/api/status",
            json={"server_id": server_id, "status": status},
            verify=False,
            timeout=5,
        )
        print(f"Status change: {server_id} -> {status}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending status change to API: {e}")


def handle_client(conn: socket.socket, addr):
    """Handle a single TCP client connection."""
    print(f"Client connected: {addr}")
    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) != 6 or parts[0] != "HEARTBEAT":
                    print(f"Invalid message from {addr}: {line}")
                    continue

                _, server_id, timestamp, cpu, mem, status = parts

                with lock:
                    last_heartbeat[server_id] = time.time()

                    # If server was marked DOWN, it's back UP
                    if server_id in servers_down:
                        servers_down.discard(server_id)
                        send_status_change(server_id, "UP")

                send_heartbeat_to_api({
                    "server_id": server_id,
                    "cpu": float(cpu),
                    "mem": float(mem),
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                ack = f"ACK|{server_id}\n"
                conn.sendall(ack.encode("utf-8"))

    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        print(f"Client {addr} disconnected: {e}")
    finally:
        conn.close()
        print(f"Client disconnected: {addr}")


def check_timeouts():
    """Periodically check for servers that missed their heartbeat."""
    while True:
        time.sleep(5)
        now = time.time()
        with lock:
            for server_id, last_time in list(last_heartbeat.items()):
                if now - last_time > HEARTBEAT_TIMEOUT:
                    if server_id not in servers_down:
                        servers_down.add(server_id)
                        send_status_change(server_id, "DOWN")


def main():
    """Start the TCP server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", TCP_PORT))
    server_socket.listen(5)
    print(f"TCP server listening on port {TCP_PORT}")

    timeout_thread = threading.Thread(target=check_timeouts, daemon=True)
    timeout_thread.start()

    while True:
        conn, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        client_thread.start()


if __name__ == "__main__":
    main()
