from typing import Any

from qdrant_client import QdrantClient
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal

async def check_database() -> bool:
    """Return whether PostgreSQL is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        return True

    except Exception:
        return False


def check_redis() -> bool:
    """Return whether Redis is reachable."""
    try:
        import redis

        client = redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

        try:
            return bool(client.ping())
        finally:
            client.close()

    except Exception:
        return False


def check_qdrant() -> bool:
    """Return whether Qdrant is reachable."""
    try:
        client = QdrantClient(
            url=settings.qdrant_url,
            timeout=2,
        )

        try:
            client.get_collections()
        finally:
            client.close()

        return True

    except Exception:
        return False


async def check_readiness() -> dict[str, Any]:
    """Check all infrastructure dependencies."""
    database_ok = await check_database()
    redis_ok = check_redis()
    qdrant_ok = check_qdrant()

    dependencies = {
        "database": (
            "healthy"
            if database_ok
            else "unhealthy"
        ),
        "redis": (
            "healthy"
            if redis_ok
            else "unhealthy"
        ),
        "qdrant": (
            "healthy"
            if qdrant_ok
            else "unhealthy"
        ),
    }

    ready = all(
        (
            database_ok,
            redis_ok,
            qdrant_ok,
        )
    )

    return {
        "status": "ready" if ready else "not_ready",
        "dependencies": dependencies,
    }