"""
Entry point for scheduled (cron) runs.
Books today's session using the preferred slots defined in .env.

Run with:
    python main.py
"""

import asyncio
import logging

import booker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

if __name__ == "__main__":
    asyncio.run(booker.book())
