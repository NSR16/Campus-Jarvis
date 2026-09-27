
import asyncio
import selectors
import sys

import psycopg

from app.core.config import get_settings
from app.db.connection import get_database_config
from app.db.schema import initialize_schema


async def main() -> None:
    database_config = get_database_config(get_settings())

    async with await psycopg.AsyncConnection.connect(
        database_config.dsn
    ) as connection:
        await initialize_schema(connection)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(
            main(),
            loop_factory=lambda: asyncio.SelectorEventLoop(
                selectors.SelectSelector()
            ),
        )
    else:
        asyncio.run(main())