import asyncio
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


load_dotenv(".env")

os.environ["APP_ENV"] = "testing"
os.environ["EMBEDDING_PROVIDER"] = "deterministic"

postgres_user = os.getenv(
    "POSTGRES_USER",
    "bom_admin",
)

postgres_password = os.getenv(
    "POSTGRES_PASSWORD",
    "",
)

postgres_host = os.getenv(
    "POSTGRES_TEST_HOST",
    "localhost",
)

postgres_port = os.getenv(
    "POSTGRES_PORT",
    "5432",
)

postgres_db = os.getenv(
    "POSTGRES_TEST_DB",
    "bom_intelligence_test",
)

if not postgres_password:
    raise RuntimeError(
        "POSTGRES_PASSWORD must be configured before running tests."
    )

encoded_password = quote_plus(postgres_password)

test_database_url = (
    "postgresql+asyncpg://"
    f"{postgres_user}:{encoded_password}@"
    f"{postgres_host}:{postgres_port}/"
    f"{postgres_db}"
)

os.environ["DATABASE_URL"] = test_database_url


async def _reset_test_database() -> None:
    """
    Reset application data in the dedicated PostgreSQL
    test database.

    The production database is never touched.
    """

    engine = create_async_engine(
        test_database_url,
        poolclass=NullPool,
    )

    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    TRUNCATE TABLE
                        alternative_records,
                        bom_risk_records,
                        bom_components,
                        ingestion_records,
                        document_ingestion_records,
                        lifecycle_records,
                        risk_records,
                        components,
                        boms
                    RESTART IDENTITY CASCADE
                    """
                )
            )
    finally:
        await engine.dispose()


def pytest_sessionstart(session) -> None:
    """
    Reset the dedicated test database before pytest runs.
    """

    del session

    asyncio.run(
        _reset_test_database()
    )