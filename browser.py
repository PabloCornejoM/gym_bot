import asyncio
import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

import config
import notifier

log = logging.getLogger("GymBot.browser")


async def login(page: Page) -> None:
    log.info("Opening login page...")
    await page.goto(config.GYM_URL, wait_until="networkidle")
    await page.screenshot(path="01_login.png")

    rut_field = await page.wait_for_selector(
        "input[type='text'], input[name*='rut' i], input[id*='rut' i], input[placeholder*='rut' i]",
        timeout=10_000,
    )
    await rut_field.fill(config.RUT)
    await page.click("button:has-text('Ingresar'), input[type='submit'], button[type='submit']")
    await page.wait_for_load_state("networkidle")
    await page.screenshot(path="02_calendar.png")
    log.info("Login successful.")


async def open_day_modal(page: Page, date_iso: str, day: str) -> None:
    log.info(f"Looking for {date_iso} on the calendar...")
    await page.wait_for_selector("td, .fc-day, [class*='day']", timeout=10_000)
    await asyncio.sleep(1)

    cell = await _find_cell_by_date_attr(page, date_iso) or await _find_cell_by_day_number(page, day)

    if not cell:
        await page.screenshot(path="error_no_cell.png")
        notifier.send_photo("error_no_cell.png", f"GymBot: could not find cell for {date_iso}")
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


async def select_slot(page: Page, slot_override: str | None = None) -> str:
    select = await page.wait_for_selector(
        "select[name*='bloque' i], select[id*='bloque' i]",
        state="attached",
        timeout=5_000,
    )
    slots_to_try = ([slot_override] if slot_override else []) + config.PREFERRED_SLOTS

    for preferred in slots_to_try:
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

    log.warning("No preferred slot available — picking first available.")
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
