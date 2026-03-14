"""
TCP Heartbeat Agent — Person 1

Simulates a monitored server by sending periodic heartbeats to the TCP server.

Protocol format:
  Agent -> Server:  HEARTBEAT|<server_id>|<timestamp>|<cpu>|<mem>|<status>
  Server -> Agent:  ACK|<server_id>

Environment variables:
  TCP_SERVER_HOST  — hostname of TCP server (default: localhost)
  TCP_SERVER_PORT  — port of TCP server (default: 9000)
  SERVER_ID        — unique identifier for this agent (default: agent-01)
"""

import socket
import time
import os
import random

TCP_SERVER_HOST = os.environ.get("TCP_SERVER_HOST", "localhost")
TCP_SERVER_PORT = int(os.environ.get("TCP_SERVER_PORT", 9000))
SERVER_ID = os.environ.get("SERVER_ID", "agent-01")
HEARTBEAT_INTERVAL = 10  # seconds


def create_heartbeat_message() -> str:
    """Build a heartbeat message with simulated metrics."""
    timestamp = int(time.time())
    cpu = random.randint(5, 95)
    mem = random.randint(20, 90)
    status = "OK"
    return f"HEARTBEAT|{SERVER_ID}|{timestamp}|{cpu}|{mem}|{status}"


def main():
    """Connect to TCP server and send heartbeats in a loop."""
    # TODO: Person 1 — implement the agent
    #
    # 1. Create a TCP socket: socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 2. Connect to (TCP_SERVER_HOST, TCP_SERVER_PORT)
    #    - Retry with backoff if connection fails
    # 3. In a loop:
    #    a. Build message with create_heartbeat_message()
    #    b. Send it: sock.sendall((message + "\n").encode())
    #    c. Receive ACK: sock.recv(1024).decode()
    #    d. Print status
    #    e. Sleep HEARTBEAT_INTERVAL seconds
    # 4. Handle disconnection — try to reconnect
    pass


if __name__ == "__main__":
    main()
