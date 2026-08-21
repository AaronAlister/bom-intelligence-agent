import asyncio

from sqlalchemy import text

from backend.app.db.session import engine


async def main():
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'bom_components'::regclass
                  AND contype = 'f'
                """
            )
        )

        for row in result:
            print(row[0])

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())