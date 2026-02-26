"""Discover cafe clubId and board menuIds from the cafe main page."""

import asyncio
import re

from loguru import logger
from playwright.async_api import BrowserContext

from src.config import settings
from src.models import Board


async def discover_boards(context: BrowserContext) -> list[Board]:
    """Navigate to cafe main page and extract clubId + target board menuIds.

    Uses the cafe's left-side menu to find board names matching
    the configured target_boards list.

    Args:
        context: Authenticated Playwright BrowserContext.

    Returns:
        List of Board objects with menu_id, menu_name, club_id, and category.
    """
    page = await context.new_page()
    boards: list[Board] = []

    try:
        await page.goto(settings.cafe_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Extract clubId from page source or URL
        club_id = await _extract_club_id(page)
        if not club_id:
            logger.error("clubId를 찾을 수 없습니다.")
            return boards

        logger.info(f"clubId: {club_id}")

        # Access the cafe_main iframe for menu navigation
        frame = page.frame("cafe_main")
        if not frame:
            # Try to find iframe by selector
            iframe_el = await page.query_selector("iframe#cafe_main")
            if iframe_el:
                frame = await iframe_el.content_frame()

        # Fallback: parse menu from main page source
        if not frame:
            logger.info("iframe 없이 메인 페이지에서 메뉴를 탐색합니다.")
            frame = page

        # Try to find menu links in the sidebar
        menu_links = await page.query_selector_all(
            "a[href*='menuid='], a[href*='search.menuid=']"
        )

        if not menu_links:
            # Try within the whole page content
            content = await page.content()
            boards = _parse_boards_from_html(content, club_id)
            if boards:
                return boards

        seen_menu_ids: set[int] = set()
        for link in menu_links:
            text = (await link.inner_text()).strip()
            href = await link.get_attribute("href") or ""

            for target in settings.target_boards:
                if target in text or text in target:
                    menu_id = _extract_menu_id(href)
                    if menu_id and menu_id not in seen_menu_ids:
                        seen_menu_ids.add(menu_id)
                        category = _clean_category(text)
                        board = Board(
                            menu_id=menu_id,
                            menu_name=text,
                            club_id=club_id,
                            category=category,
                        )
                        boards.append(board)
                        logger.info(
                            f"게시판 발견: {text} (menuId={menu_id})"
                        )
                    break

    except Exception as e:
        logger.error(f"게시판 탐색 중 오류: {e}")
    finally:
        await page.close()

    if not boards:
        logger.warning(
            "자동 탐색에 실패했습니다. "
            "수동으로 menuId를 확인해주세요."
        )

    return boards


async def _extract_club_id(page: object) -> int | None:
    """Extract the numeric clubId from page content or scripts.

    Args:
        page: Playwright Page object.

    Returns:
        Integer clubId or None if not found.
    """
    content = await page.content()

    # Pattern 1: clubid in JavaScript variables
    patterns = [
        r'"clubId"\s*:\s*(\d+)',
        r"clubid\s*=\s*(\d+)",
        r"club\.id\s*=\s*(\d+)",
        r"search\.clubid=(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return int(match.group(1))

    # Pattern 2: from URL parameters
    url = page.url
    match = re.search(r"clubid=(\d+)", url, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _extract_menu_id(href: str) -> int | None:
    """Extract menuId from a menu link href.

    Args:
        href: The href attribute string from a menu link.

    Returns:
        Integer menuId or None if not found.
    """
    match = re.search(r"menuid=(\d+)", href, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _clean_category(menu_name: str) -> str:
    """Remove decorative characters from board name to get clean category.

    Args:
        menu_name: Raw board name with possible decorative chars.

    Returns:
        Cleaned category string (e.g. '중앙공기업').
    """
    cleaned = re.sub(r"[★●▶▷■□◆◇※☆·\s]", "", menu_name)
    return cleaned


def _parse_boards_from_html(
    html: str, club_id: int
) -> list[Board]:
    """Fallback: parse board info directly from page HTML.

    Args:
        html: Full HTML content of the page.
        club_id: The cafe's clubId.

    Returns:
        List of Board objects found in the HTML.
    """
    boards: list[Board] = []
    # Look for menu links with menuid parameter
    pattern = r'href="[^"]*menuid=(\d+)[^"]*"[^>]*>([^<]*(?:중앙공기업|지방공기업|대학/기타기관|대학기타기관)[^<]*)<'
    matches = re.findall(pattern, html, re.IGNORECASE)

    for menu_id_str, name in matches:
        name = name.strip()
        boards.append(
            Board(
                menu_id=int(menu_id_str),
                menu_name=name,
                club_id=club_id,
                category=_clean_category(name),
            )
        )
        logger.info(
            f"HTML에서 게시판 발견: {name} (menuId={menu_id_str})"
        )

    return boards
