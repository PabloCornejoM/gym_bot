import asyncio
import logging
import os

import requests
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

RUT = os.getenv("RUT", "")
GYM_URL = os.getenv("GYM_URL", "https://www.agendaqr.cl/agenda/24/ingresar")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
PREFERRED_SLOTS = [
    s.strip()
    for s in os.getenv("PREFERRED_SLOTS", "08:00 - 09:00,09:00 - 10:00,10:00 - 11:00").split(",")
]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("GymBot")

# ── Telegram ──────────────────────────────────────────────────────────────────

def _telegram_configured() -> bool:
    return bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def notify(photo_path: str, caption: str) -> None:
    if not _telegram_configured():
        log.warning("Telegram not configured — skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": photo},
                timeout=15,
            )
        log.info("Notification sent via Telegram.")
    except Exception as exc:
        log.warning(f"Could not send Telegram notification: {exc}")


# ── Browser steps ─────────────────────────────────────────────────────────────

async def login(page: Page) -> None:
    log.info("Opening login page...")
    await page.goto(GYM_URL, wait_until="networkidle")
    await page.screenshot(path="01_login.png")

    rut_field = await page.wait_for_selector(
        "input[type='text'], input[name*='rut' i], input[id*='rut' i], input[placeholder*='rut' i]",
        timeout=10_000,
    )
    await rut_field.fill(RUT)
    await page.click("button:has-text('Ingresar'), input[type='submit'], button[type='submit']")
    await page.wait_for_load_state("networkidle")
    await page.screenshot(path="02_calendar.png")
    log.info("Login successful.")


async def open_day_modal(page: Page, date_iso: str, day: str) -> None:
    log.info(f"Looking for day {day} ({date_iso}) on the calendar...")
    await page.wait_for_selector("td, .fc-day, [class*='day']", timeout=10_000)
    await asyncio.sleep(1)

    cell = await _find_cell_by_date_attr(page, date_iso)
    if not cell:
        cell = await _find_cell_by_day_number(page, day)

    if not cell:
        await page.screenshot(path="error_no_cell.png")
        notify("error_no_cell.png", f"GymBot: could not find cell for {date_iso}")
        raise RuntimeError(f"Calendar cell not found for {date_iso}")

    await cell.click()
    await asyncio.sleep(2)
    await page.screenshot(path="03_modal.png")

    await page.wait_for_selector(
        ".modal.in, .modal.show, dialog, [role='dialog']",
        state="attached",
        timeout=12_000,
    )
    await asyncio.sleep(0.5)
    log.info("Modal open.")


async def _find_cell_by_date_attr(page: Page, date_iso: str):
    for selector in [
        f"td[data-date='{date_iso}']",
        f".fc-day[data-date='{date_iso}']",
        f"[data-date='{date_iso}']",
    ]:
        cell = await page.query_selector(selector)
        if cell:
            log.info(f"Cell found via: {selector}")
            return cell
    return None


async def _find_cell_by_day_number(page: Page, day: str):
    log.info("Falling back to day-number search...")
    cells = await page.query_selector_all("td.fc-day-top, td[class*='day'], .fc-daygrid-day, td")
    for cell in cells:
        text = (await cell.inner_text()).strip()
        if text == day or text.startswith(day + "\n"):
            log.info(f"Cell found by text: '{text[:30]}'")
            return cell
    return None


async def select_branch(page: Page) -> None:
    try:
        select = await page.wait_for_selector(
            "select[name*='sucursal' i], select[id*='sucursal' i]",
            state="attached",
            timeout=5_000,
        )
        for option in await select.query_selector_all("option"):
            value = await option.get_attribute("value")
            if value and value not in ("", "0"):
                await select.select_option(value=value)
                log.info(f"Branch: {(await option.inner_text()).strip()}")
                break
        await asyncio.sleep(0.5)
    except PlaywrightTimeout:
        log.warning("Branch selector not found — skipping.")


async def select_slot(page: Page) -> str:
    select = await page.wait_for_selector(
        "select[name*='bloque' i], select[id*='bloque' i]",
        state="attached",
        timeout=5_000,
    )
    for preferred in PREFERRED_SLOTS:
        preferred_clean = preferred.replace(" ", "")
        for option in await select.query_selector_all("option"):
            text = await option.inner_text()
            if preferred_clean in text.replace(" ", ""):
                value = await option.get_attribute("value")
                await select.select_option(value=value)
                slot = text.strip()
                log.info(f"Slot: {slot}")
                await asyncio.sleep(0.5)
                return slot

    log.warning("Preferred slot unavailable — picking first available.")
    for option in await select.query_selector_all("option"):
        value = await option.get_attribute("value")
        if value and value not in ("", "0"):
            await select.select_option(value=value)
            slot = (await option.inner_text()).strip()
            log.info(f"Slot: {slot}")
            await asyncio.sleep(0.5)
            return slot

    return ""


async def select_activity(page: Page) -> str:
    try:
        select = await page.wait_for_selector(
            "select[name*='actividad' i], select[id*='actividad' i]",
            state="attached",
            timeout=5_000,
        )
        for option in await select.query_selector_all("option"):
            value = await option.get_attribute("value")
            if value and value not in ("", "0"):
                await select.select_option(value=value)
                activity = (await option.inner_text()).strip()
                log.info(f"Activity: {activity}")
                await asyncio.sleep(0.5)
                return activity
    except PlaywrightTimeout:
        log.warning("Activity selector not found — skipping.")
    return ""


async def check_oath_checkbox(page: Page) -> None:
    for checkbox in await page.query_selector_all("input[type='checkbox']"):
        if not await checkbox.is_checked():
            await checkbox.evaluate("el => el.click()")
            log.info("Oath checkbox checked.")
    await asyncio.sleep(0.3)


async def submit_booking(page: Page) -> None:
    await page.screenshot(path="04_before_submit.png")
    button = await page.wait_for_selector(
        "button:has-text('Guardar'), input[value*='Guardar' i]",
        state="attached",
        timeout=5_000,
    )
    await button.evaluate("el => el.click()")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(2)
    await page.screenshot(path="05_result.png")
    log.info("Booking submitted.")


# ── Main flow ─────────────────────────────────────────────────────────────────

async def book() -> None:
    today = datetime.now()
    date_iso = today.strftime("%Y-%m-%d")
    day = str(today.day)
    log.info(f"Booking for: {today.strftime('%d/%m/%Y')}")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=HEADLESS, slow_mo=500)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = await context.new_page()

        try:
            await login(page)
            await open_day_modal(page, date_iso, day)
            await select_branch(page)
            slot = await select_slot(page)
            activity = await select_activity(page)
            await check_oath_checkbox(page)
            await submit_booking(page)

            caption = (
                f"Booking confirmed for {today.strftime('%d/%m/%Y')}\n"
                f"Slot: {slot}\n"
                f"Activity: {activity}"
            )
            notify("05_result.png", caption)

        except PlaywrightTimeout as exc:
            log.error(f"Timeout: {exc}")
            await page.screenshot(path="error.png")
            notify("error.png", f"GymBot failed (timeout) — {date_iso}")
        except Exception as exc:
            log.error(f"Error: {exc}")
            await page.screenshot(path="error.png")
            notify("error.png", f"GymBot failed — {date_iso}\n{exc}")
            raise
        finally:
            await asyncio.sleep(3)
            await browser.close()


if __name__ == "__main__":
    log.info("GymBot starting...")
    asyncio.run(book())
    log.info("GymBot done.")
