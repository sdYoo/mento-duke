"""Naver Cafe Job Posting Scraper - CLI Entry Point.

Usage:
    python main.py login              # Manual Naver login → save cookies
    python main.py scrape             # Run full scraping pipeline (headless)
    python main.py scrape --headed    # Run with visible browser
    python main.py scrape --pages 3   # Scrape up to 3 pages per board
    python main.py scrape --keywords "전산,IT"  # Multiple keywords
    python main.py scrape --today     # Only today's postings
"""

import asyncio
import sys
from datetime import date, datetime, timezone, timedelta

import typer
from loguru import logger

from src.config import settings, DATA_DIR, LOGS_DIR

# Configure loguru
logger.remove()
logger.add(sys.stderr, level="INFO", format=(
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{message}</cyan>"
))
logger.add(
    LOGS_DIR / "scraper_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
)

app = typer.Typer(
    name="naver-cafe-scraper",
    help="네이버 카페 채용공고 스크래퍼",
)


@app.command()
def login() -> None:
    """Open browser for manual Naver login and save cookies.

    Args:
        None.

    Returns:
        None. Saves cookies to data/cookies.json.
    """
    asyncio.run(_login())


async def _login() -> None:
    """Async login flow."""
    from playwright.async_api import async_playwright
    from src.auth import login_and_save_cookies

    async with async_playwright() as pw:
        await login_and_save_cookies(pw, settings.cookies_path)


@app.command()
def scrape(
    headed: bool = typer.Option(
        False, "--headed", help="브라우저를 표시합니다."
    ),
    pages: int = typer.Option(
        None, "--pages", "-p", help="게시판당 탐색할 페이지 수"
    ),
    keywords: str = typer.Option(
        None, "--keywords", "-k",
        help="필터링 키워드 (쉼표 구분, 예: '전산,IT')",
    ),
    today: bool = typer.Option(
        False, "--today", "-t", help="오늘 올라온 공고만 필터링"
    ),
) -> None:
    """Run the full scraping pipeline.

    Args:
        headed: If True, show the browser window.
        pages: Override number of pages to scrape per board.
        keywords: Comma-separated filter keywords.
        today: If True, only include articles posted today.

    Returns:
        None. Outputs results to data/ directory.
    """
    keyword_list = (
        [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if keywords
        else [settings.keyword]
    )
    asyncio.run(_scrape(headed, pages, keyword_list, today))


async def _scrape(
    headed: bool,
    pages: int | None,
    keywords: list[str],
    today_only: bool,
) -> None:
    """Async scraping pipeline."""
    from playwright.async_api import async_playwright
    from src.auth import cookies_exist, create_authenticated_context
    from src.exporter import export_results, export_txt
    from src.models import JobPosting
    from tasks.discover import discover_boards
    from tasks.scrape_details import scrape_article_details
    from tasks.scrape_listings import scrape_board_listings

    # Validate cookies
    if not cookies_exist(settings.cookies_path):
        logger.error(
            "쿠키 파일이 없습니다. "
            "'python main.py login' 을 먼저 실행해주세요."
        )
        raise typer.Exit(code=1)

    headless = not headed
    scrape_pages = pages or settings.scrape_pages
    kw_display = ", ".join(keywords)

    logger.info(f"스크래핑 시작: 카페={settings.cafe_id}")
    logger.info(f"키워드=[{kw_display}], 페이지={scrape_pages}")
    if today_only:
        logger.info("오늘 날짜 공고만 필터링합니다.")

    async with async_playwright() as pw:
        context = await create_authenticated_context(
            pw, settings.cookies_path, headless=headless
        )

        try:
            # Step 1: Discover boards
            logger.info("Step 1/4: 게시판 탐색 중...")
            boards = await discover_boards(context)

            if not boards:
                logger.error(
                    "대상 게시판을 찾을 수 없습니다. "
                    "카페 URL과 게시판 이름을 확인해주세요."
                )
                raise typer.Exit(code=1)

            logger.info(f"{len(boards)}개 게시판 발견")

            # Step 2: Scrape listings from all boards
            logger.info("Step 2/4: 게시글 목록 수집 중...")
            all_articles = []
            for board in boards:
                articles = await scrape_board_listings(
                    context,
                    board,
                    pages=scrape_pages,
                    keywords=keywords,
                )
                all_articles.extend(articles)

            if not all_articles:
                logger.warning(
                    f"[{kw_display}] 키워드가 포함된 "
                    "게시글을 찾지 못했습니다."
                )
                raise typer.Exit(code=0)

            logger.info(f"총 {len(all_articles)}건 게시글 수집")

            # Filter by today's date if requested
            if today_only:
                all_articles = _filter_today(all_articles)
                logger.info(
                    f"오늘 날짜 필터 적용 후: {len(all_articles)}건"
                )
                if not all_articles:
                    logger.warning("오늘 올라온 공고가 없습니다.")
                    raise typer.Exit(code=0)

            # Step 3: Scrape details
            logger.info("Step 3/4: 게시글 상세 정보 추출 중...")
            postings = await scrape_article_details(
                context, all_articles
            )

            # Step 4: Export results
            logger.info("Step 4/4: 결과 저장 중...")
            export_results(
                postings,
                settings.output_md,
                settings.output_csv,
            )

            # Export dated txt file
            today_str = date.today().strftime("%Y-%m-%d")
            txt_path = DATA_DIR / f"{today_str}.txt"
            export_txt(
                postings,
                txt_path,
                title=f"채용공고 스크래핑 결과 ({today_str})",
            )

        finally:
            await context.browser.close()

    logger.success("스크래핑 완료!")


def _filter_today(
    articles: list,
) -> list:
    """Filter articles to only include those posted today.

    Uses write_timestamp (epoch ms) if available. Falls back to
    checking write_date text for today's date or time-only format.

    Args:
        articles: List of ArticleSummary objects.

    Returns:
        Filtered list containing only today's articles.
    """
    import re

    kst = timezone(timedelta(hours=9))
    today_kst = datetime.now(kst).date()
    today_str = today_kst.strftime("%Y.%m.%d")
    today_short = today_kst.strftime("%m.%d")

    filtered = []
    for article in articles:
        # Method 1: Use timestamp if available
        if article.write_timestamp > 0:
            article_date = datetime.fromtimestamp(
                article.write_timestamp / 1000, tz=kst
            ).date()
            if article_date == today_kst:
                filtered.append(article)
                continue
            else:
                continue

        # Method 2: Check write_date text
        wd = article.write_date
        if not wd:
            continue

        # If it contains today's date string
        if today_str in wd or today_short in wd:
            filtered.append(article)
            continue

        # If it's a time-only format (no date = today)
        # e.g., "10:30", "1시간 전", "방금 전", "몇분 전"
        if re.match(r"^\d{1,2}:\d{2}$", wd):
            filtered.append(article)
            continue
        if "분 전" in wd or "시간 전" in wd or "방금" in wd:
            filtered.append(article)
            continue

    return filtered


if __name__ == "__main__":
    app()
