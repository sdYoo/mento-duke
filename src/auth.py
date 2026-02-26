"""Authentication module for Naver login via Playwright.

Handles manual login flow, cookie persistence, and session validation.
"""

import json
from pathlib import Path

from loguru import logger
from playwright.async_api import BrowserContext, Playwright


NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
NAVER_COOKIE_NAMES = {"NID_AUT", "NID_SES"}


async def login_and_save_cookies(
    pw: Playwright, cookies_path: Path
) -> None:
    """Open a browser for manual Naver login and save cookies.

    Args:
        pw: Playwright instance.
        cookies_path: File path to save the storage state JSON.

    Returns:
        None. Saves cookies to cookies_path on success.
    """
    browser = await pw.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(NAVER_LOGIN_URL)
    logger.info("브라우저가 열렸습니다. 네이버에 로그인해주세요.")
    logger.info("로그인 완료 후 자동으로 쿠키가 저장됩니다. (최대 5분 대기)")

    # Poll for login cookies every 3 seconds, up to 5 minutes
    max_wait = 300
    elapsed = 0
    interval = 3

    while elapsed < max_wait:
        await page.wait_for_timeout(interval * 1000)
        elapsed += interval

        try:
            cookies = await context.cookies()
        except Exception:
            # Browser was closed by user
            logger.error("브라우저가 닫혔습니다.")
            return

        cookie_names = {c["name"] for c in cookies}
        if NAVER_COOKIE_NAMES.issubset(cookie_names):
            logger.info("로그인 쿠키 감지!")
            break
    else:
        logger.error("5분 내 로그인이 완료되지 않았습니다.")
        await browser.close()
        return

    # Save storage state
    cookies_path.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(cookies_path))
    logger.success(f"쿠키가 저장되었습니다: {cookies_path}")

    await browser.close()


def cookies_exist(cookies_path: Path) -> bool:
    """Check if saved cookies file exists and contains valid data.

    Args:
        cookies_path: Path to the cookies JSON file.

    Returns:
        True if cookies file exists and contains Naver auth cookies.
    """
    if not cookies_path.exists():
        return False

    try:
        data = json.loads(cookies_path.read_text(encoding="utf-8"))
        cookie_names = {c["name"] for c in data.get("cookies", [])}
        return NAVER_COOKIE_NAMES.issubset(cookie_names)
    except (json.JSONDecodeError, KeyError):
        return False


async def create_authenticated_context(
    pw: Playwright, cookies_path: Path, *, headless: bool = True
) -> BrowserContext:
    """Create a Playwright browser context with saved cookies.

    Args:
        pw: Playwright instance.
        cookies_path: Path to the saved storage state JSON.
        headless: Whether to run browser in headless mode.

    Returns:
        Authenticated BrowserContext ready for scraping.

    Raises:
        FileNotFoundError: If cookies file does not exist.
    """
    if not cookies_path.exists():
        raise FileNotFoundError(
            f"쿠키 파일이 없습니다: {cookies_path}\n"
            "'python main.py login' 을 먼저 실행해주세요."
        )

    browser = await pw.chromium.launch(headless=headless)
    context = await browser.new_context(storage_state=str(cookies_path))
    logger.info("저장된 쿠키로 인증 컨텍스트를 생성했습니다.")
    return context
