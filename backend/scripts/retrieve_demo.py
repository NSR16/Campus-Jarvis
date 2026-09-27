import asyncio
import selectors
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.connection import create_connection_pool
from app.services.retrieval import retrieve_chunks

QUERIES = (
    "When does the campus library close?",
    "Is the library open on public holidays?",
)


async def main() -> None:
    pool = create_connection_pool(get_settings())
    try:
        await pool.open(wait=True)
        for query in QUERIES:
            print(f"\nQuery: {query}")
            results = await retrieve_chunks(query, pool)
            if not results:
                print("No matching chunks found.")
                continue

            for result in results:
                print(
                    f"[{result.distance:.4f}] {result.title} "
                    f"({result.document_type}) - {result.source}, "
                    f"chunk {result.chunk_index}"
                )
                print(result.content)
    finally:
        await pool.close()


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