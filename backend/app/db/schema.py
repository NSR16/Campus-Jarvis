from pathlib import Path

from psycopg import AsyncConnection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")


async def initialize_schema(connection: AsyncConnection) -> None:
    """Execute the checked-in, repeatable schema script on the given connection."""
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    await connection.execute(schema_sql, prepare=False)