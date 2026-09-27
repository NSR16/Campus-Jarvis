import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.generation import generate_text

PROMPT = "Reply with exactly: CAMPUS JARVIS GENERATION OK"


async def main() -> None:
    response = await generate_text(PROMPT, get_settings())
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
