import logging
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

import browser
import config
import notifier

log = logging.getLogger("GymBot.booker")


async def book(slot_override: str | None = None) -> None:
    today = datetime.now() + timedelta(days=0)
    date_iso = today.strftime("%Y-%m-%d")
    day = str(today.day)
    log.info(f"Booking for: {today.strftime('%d/%m/%Y')}")

    async with async_playwright() as playwright:
        chromium = await playwright.chromium.launch(headless=config.HEADLESS)
        context = await chromium.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = await context.new_page()

        try:
            await browser.login(page)
            await browser.open_day_modal(page, date_iso, day)
            await browser.select_branch(page)
            slot = await browser.select_slot(page, slot_override)
            activity = await browser.select_activity(page)
            await browser.check_oath_checkbox(page)
            await browser.submit_booking(page)

            caption = (
                f"Booking confirmed for {today.strftime('%d/%m/%Y')}\n"
                f"Slot: {slot}\n"
                f"Activity: {activity}"
            )
            notifier.send_photo("05_result.png", caption)

        except PlaywrightTimeout as exc:
            log.error(f"Timeout: {exc}")
            await page.screenshot(path="error.png")
            notifier.send_photo("error.png", f"GymBot failed (timeout) — {date_iso}")
        except Exception as exc:
            log.error(f"Error: {exc}")
            await page.screenshot(path="error.png")
            notifier.send_photo("error.png", f"GymBot failed — {date_iso}\n{exc}")
            raise
        finally:
            await chromium.close()
