"""
TCP Heartbeat Agent

Simulates a monitored server by sending periodic heartbeats to the TCP server.

Protocol format:
  Agent -> Server:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>
  Server -> Agent:  ACK|<server_id>
"""

import socket
import time
import os
import random

TCP_SERVER_HOST = os.environ.get("TCP_SERVER_HOST", "localhost")
TCP_SERVER_PORT = int(os.environ.get("TCP_SERVER_PORT", 9000))
SERVER_ID = os.environ.get("SERVER_ID", "agent-01")
HEARTBEAT_INTERVAL = 10


def create_heartbeat_message() -> str:
    """Build a heartbeat message with simulated metrics."""
    timestamp = int(time.time())
    cpu = random.randint(5, 95)
    mem = random.randint(20, 90)
    status = "OK"
    return f"HEARTBEAT|{SERVER_ID}|{timestamp}|{cpu}|{mem}|{status}"


def main():
    """Connect to TCP server and send heartbeats in a loop."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_SERVER_HOST, TCP_SERVER_PORT))
            print(f"Connected to {TCP_SERVER_HOST}:{TCP_SERVER_PORT} as {SERVER_ID}")

            while True:
                message = create_heartbeat_message()
                sock.sendall((message + "\n").encode("utf-8"))

                response = sock.recv(1024).decode("utf-8").strip()
                print(f"Sent: {message} | Received: {response}")

                time.sleep(HEARTBEAT_INTERVAL)

        except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"Connection error: {e}. Retrying in 5s...")
            time.sleep(5)
        finally:
            try:
                sock.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
