import logging

import requests

import config

log = logging.getLogger("GymBot.notifier")


def _configured() -> bool:
    return bool(config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID)


def send_message(text: str) -> None:
    if not _configured():
        log.warning("Telegram not configured — skipping message.")
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": config.TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except Exception as exc:
        log.warning(f"Could not send Telegram message: {exc}")


def send_photo(photo_path: str, caption: str = "") -> None:
    if not _configured():
        log.warning("Telegram not configured — skipping photo.")
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            requests.post(
                url,
                data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": photo},
                timeout=15,
            )
        log.info("Notification sent via Telegram.")
    except Exception as exc:
        log.warning(f"Could not send Telegram photo: {exc}")
