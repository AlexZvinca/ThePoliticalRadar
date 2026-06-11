from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.sentiment import SentimentAnalyzer


async def main() -> None:
    status = await SentimentAnalyzer(get_settings()).check_azure_connection()
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
