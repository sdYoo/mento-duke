"""Scrape article listings from Naver Cafe boards using REST API."""

import asyncio

import httpx
from loguru import logger
from playwright.async_api import BrowserContext

from src.config import settings
from src.models import ArticleSummary, Board


API_BASE = "https://apis.naver.com/cafe-web/cafe2/ArticleListV2dot1.json"


async def scrape_board_listings(
    context: BrowserContext,
    board: Board,
    *,
    pages: int | None = None,
    keywords: list[str] | None = None,
) -> list[ArticleSummary]:
    """Fetch article listings from a single board via Naver API.

    First attempts the REST API approach. Falls back to DOM scraping
    if the API fails.

    Args:
        context: Authenticated Playwright BrowserContext.
        board: Board object with club_id and menu_id.
        pages: Number of pages to scrape (default: settings.scrape_pages).
        keywords: Filter keywords list (default: [settings.keyword]).

    Returns:
        List of ArticleSummary objects matching any keyword filter.
    """
    pages = pages or settings.scrape_pages
    keywords = keywords or [settings.keyword]

    # Extract only required auth cookies from context for httpx
    required_names = {"NID_AUT", "NID_SES"}
    cookies = await context.cookies()
    cookie_header = "; ".join(
        f"{c['name']}={c['value']}"
        for c in cookies
        if c["name"] in required_names
    )

    articles = await _fetch_via_api(
        board, cookie_header, pages, keywords
    )

    if articles is None:
        logger.warning(
            f"API 실패, DOM 파싱으로 전환: {board.menu_name}"
        )
        articles = await _fetch_via_dom(
            context, board, pages, keywords
        )

    kw_display = ", ".join(keywords)
    logger.info(
        f"[{board.category}] '{kw_display}' 포함 게시글 "
        f"{len(articles)}건 발견"
    )
    return articles


async def _fetch_via_api(
    board: Board,
    cookie_header: str,
    pages: int,
    keywords: list[str],
) -> list[ArticleSummary] | None:
    """Fetch listings using Naver Cafe REST API.

    Args:
        board: Board with club_id and menu_id.
        cookie_header: Cookie string for authentication.
        pages: Number of pages to fetch.
        keywords: Keywords to filter article titles (match any).

    Returns:
        List of matching ArticleSummary objects, or None on API failure.
    """
    articles: list[ArticleSummary] = []
    headers = {
        "Cookie": cookie_header,
        "Referer": f"https://cafe.naver.com/{settings.cafe_id}",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=30.0
    ) as client:
        for page_num in range(1, pages + 1):
            params = {
                "search.clubid": board.club_id,
                "search.menuid": board.menu_id,
                "search.page": page_num,
                "search.perPage": 50,
            }

            try:
                resp = await client.get(API_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError) as e:
                logger.error(f"API 요청 실패 (page {page_num}): {e}")
                return None

            article_list = (
                data.get("message", {})
                .get("result", {})
                .get("articleList", [])
            )

            if not article_list:
                logger.debug(
                    f"페이지 {page_num}에 게시글이 없습니다."
                )
                break

            for item in article_list:
                title = item.get("subject", "")
                title_lower = title.lower()
                if not any(kw.lower() in title_lower for kw in keywords):
                    continue

                article_id = item.get("articleId", 0)
                article = ArticleSummary(
                    article_id=article_id,
                    title=title,
                    board_category=board.category,
                    writer=item.get("writerNickname", ""),
                    write_timestamp=item.get("writeDateTimestamp", 0),
                    link=(
                        f"https://cafe.naver.com/{settings.cafe_id}"
                        f"/{article_id}"
                    ),
                )
                articles.append(article)

            await asyncio.sleep(settings.request_delay)

    return articles


async def _fetch_via_dom(
    context: BrowserContext,
    board: Board,
    pages: int,
    keywords: list[str],
) -> list[ArticleSummary]:
    """Fallback: scrape listings by navigating the cafe page DOM.

    Args:
        context: Authenticated Playwright BrowserContext.
        board: Board with club_id and menu_id.
        pages: Number of pages to scrape.
        keywords: Keywords to filter article titles (match any).

    Returns:
        List of matching ArticleSummary objects.
    """
    articles: list[ArticleSummary] = []
    page = await context.new_page()

    try:
        for page_num in range(1, pages + 1):
            url = (
                f"https://cafe.naver.com/ArticleList.nhn"
                f"?search.clubid={board.club_id}"
                f"&search.menuid={board.menu_id}"
                f"&search.page={page_num}"
            )

            board_url = (
                f"{settings.cafe_url}?iframe_url=/ArticleList.nhn"
                f"%3Fsearch.clubid={board.club_id}"
                f"%26search.menuid={board.menu_id}"
                f"%26search.page={page_num}"
            )

            await page.goto(board_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            frame = page.frame("cafe_main")
            if not frame:
                logger.warning("cafe_main iframe을 찾을 수 없습니다.")
                continue

            rows = await frame.query_selector_all(
                "a.article, a[class*='article'], "
                ".article-board a, .board-list a"
            )

            for row in rows:
                text = (await row.inner_text()).strip()
                href = await row.get_attribute("href") or ""

                text_lower = text.lower()
                if not any(kw.lower() in text_lower for kw in keywords):
                    continue

                article_id = _extract_article_id(href)
                if not article_id:
                    continue

                articles.append(
                    ArticleSummary(
                        article_id=article_id,
                        title=text,
                        board_category=board.category,
                        link=(
                            f"https://cafe.naver.com/"
                            f"{settings.cafe_id}/{article_id}"
                        ),
                    )
                )

            await asyncio.sleep(settings.request_delay)

    except Exception as e:
        logger.error(f"DOM 파싱 중 오류: {e}")
    finally:
        await page.close()

    return articles


def _extract_article_id(href: str) -> int | None:
    """Extract article ID from a link href.

    Args:
        href: The href attribute from an article link.

    Returns:
        Integer article ID or None if not found.
    """
    import re

    match = re.search(r"/(\d+)(?:\?|$)", href)
    if match:
        return int(match.group(1))

    match = re.search(r"articleid=(\d+)", href, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None
