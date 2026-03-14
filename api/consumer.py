"""
RabbitMQ consumer — runs in a background thread alongside the FastAPI app.
Listens for heartbeat events and writes them to the database.
"""

import json
import time
from datetime import datetime
import pika
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Server, Heartbeat, Incident

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")


def process_heartbeat(data: dict, db: Session):
    """Process a server.heartbeat event."""
    server_id = data["server_id"]
    now = datetime.utcnow()

    # Upsert server record
    server = db.query(Server).filter(Server.server_id == server_id).first()
    if not server:
        server = Server(server_id=server_id, name=server_id)
        db.add(server)

    server.status = "UP"
    server.last_heartbeat = now
    server.cpu = data.get("cpu")
    server.mem = data.get("mem")

    # Record heartbeat
    heartbeat = Heartbeat(
        server_id=server_id,
        cpu=data.get("cpu", 0),
        mem=data.get("mem", 0),
        status=data.get("status", "OK"),
        timestamp=now,
    )
    db.add(heartbeat)
    db.commit()


def process_status_change(data: dict, event_type: str, db: Session):
    """Process a server.down or server.up event."""
    server_id = data["server_id"]

    server = db.query(Server).filter(Server.server_id == server_id).first()
    if server:
        server.status = event_type
        incident = Incident(
            server_id=server_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
        )
        db.add(incident)
        db.commit()


def on_message(ch, method, properties, body):
    """Callback for RabbitMQ messages."""
    db = SessionLocal()
    try:
        data = json.loads(body)
        routing_key = method.routing_key

        if routing_key == "server.heartbeat":
            process_heartbeat(data, db)
        elif routing_key == "server.down":
            process_status_change(data, "DOWN", db)
        elif routing_key == "server.up":
            process_status_change(data, "UP", db)
    except Exception as e:
        print(f"Error processing message: {e}")
        db.rollback()
    finally:
        db.close()


def start_consumer():
    """Connect to RabbitMQ and start consuming. Retries on failure."""
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            channel = connection.channel()

            channel.exchange_declare(exchange="monitor.events", exchange_type="topic")
            channel.queue_declare(queue="api_heartbeat_queue")

            channel.queue_bind(exchange="monitor.events", queue="api_heartbeat_queue", routing_key="server.heartbeat")
            channel.queue_bind(exchange="monitor.events", queue="api_heartbeat_queue", routing_key="server.down")
            channel.queue_bind(exchange="monitor.events", queue="api_heartbeat_queue", routing_key="server.up")

            channel.basic_consume(queue="api_heartbeat_queue", on_message_callback=on_message, auto_ack=True)

            print("API consumer connected to RabbitMQ")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ not ready, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"Consumer error: {e}, retrying in 5s...")
            time.sleep(5)
