import os
from dotenv import load_dotenv

load_dotenv()

RUT: str = os.getenv("RUT", "")
GYM_URL: str = os.getenv("GYM_URL", "https://www.agendaqr.cl/agenda/24/ingresar")
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
PREFERRED_SLOTS: list[str] = [
    s.strip()
    for s in os.getenv("PREFERRED_SLOTS", "08:00 - 09:00,09:00 - 10:00,10:00 - 11:00").split(",")
]

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
