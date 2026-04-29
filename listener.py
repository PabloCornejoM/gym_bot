"""
Telegram listener — runs continuously on the server.
Send any message to trigger a booking at the current hour's slot.
Include a specific time (e.g. "14:00" or "14") to book a different slot.

Run with:
    python listener.py
"""

import asyncio
import logging
import re
import time
from datetime import datetime

import requests

import booker
import config
import notifier

log = logging.getLogger("GymBot.listener")

_HOUR_PATTERN = re.compile(r"\b(\d{1,2})(?::00)?\b")


def _slot_from_hour(hour: int) -> str:
    return f"{hour:02d}:00 - {hour + 1:02d}:00"


def parse_slot(text: str) -> str | None:
    match = _HOUR_PATTERN.search(text)
    if not match:
        return None
    hour = int(match.group(1))
    if not 0 <= hour <= 23:
        return None
    return _slot_from_hour(hour)


def slot_for_now() -> str:
    return _slot_from_hour(datetime.now().hour)


def _get_updates(offset: int) -> list[dict]:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates"
    try:
        response = requests.get(
            url,
            params={"offset": offset, "timeout": 30},
            timeout=35,
        )
        return response.json().get("result", [])
    except Exception as exc:
        log.warning(f"getUpdates failed: {exc}")
        time.sleep(5)
        return []


def _is_authorized(chat_id: str) -> bool:
    return chat_id == config.TELEGRAM_CHAT_ID


def _handle_message(text: str) -> None:
    slot = parse_slot(text) or slot_for_now()
    log.info(f"Booking slot: {slot}")
    notifier.send_message(f"Got it! Booking slot {slot}...")
    asyncio.run(booker.book(slot_override=slot))


def run() -> None:
    log.info("Listener started. Waiting for Telegram messages...")
    offset = 0

    while True:
        updates = _get_updates(offset)

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "").strip()

            if not text:
                continue

            if not _is_authorized(chat_id):
                log.warning(f"Ignored message from unauthorized chat_id: {chat_id}")
                continue

            log.info(f"Message received: '{text}'")
            _handle_message(text)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run()
