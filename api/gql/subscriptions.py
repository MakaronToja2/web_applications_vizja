import strawberry
import asyncio
from typing import AsyncGenerator
from gql.types import AlertType, ServerType

# Global event queues — alert engine pushes here, subscriptions consume
_alert_subscribers: list[asyncio.Queue] = []
_status_subscribers: list[asyncio.Queue] = []


async def publish_alert(alert: AlertType):
    """Push an alert to all active subscribers."""
    for queue in _alert_subscribers:
        await queue.put(alert)


async def publish_status_change(server: ServerType):
    """Push a status change to all active subscribers."""
    for queue in _status_subscribers:
        await queue.put(server)


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def alert_triggered(self) -> AsyncGenerator[AlertType, None]:
        queue: asyncio.Queue = asyncio.Queue()
        _alert_subscribers.append(queue)
        try:
            while True:
                alert = await queue.get()
                yield alert
        finally:
            _alert_subscribers.remove(queue)

    @strawberry.subscription
    async def server_status_changed(self) -> AsyncGenerator[ServerType, None]:
        queue: asyncio.Queue = asyncio.Queue()
        _status_subscribers.append(queue)
        try:
            while True:
                server = await queue.get()
                yield server
        finally:
            _status_subscribers.remove(queue)
