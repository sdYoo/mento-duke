"""Naver Cafe Job Posting Scraper - CLI Entry Point.

Usage:
    python main.py login              # Manual Naver login → save cookies
    python main.py scrape             # Run full scraping pipeline (headless)
    python main.py scrape --headed    # Run with visible browser
    python main.py scrape --pages 3   # Scrape up to 3 pages per board
    python main.py scrape --keywords "전산,IT"  # Multiple keywords
    python main.py scrape --today     # Only today's postings
    python main.py scrape --from 2026-03-01 --to 2026-03-05  # Date range
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
    from_date: str = typer.Option(
        None, "--from", "-f", help="조회 시작 날짜 (YYYY-MM-DD)"
    ),
    to_date: str = typer.Option(
        None, "--to", help="조회 종료 날짜 (YYYY-MM-DD)"
    ),
) -> None:
    """Run the full scraping pipeline.

    Args:
        headed: If True, show the browser window.
        pages: Override number of pages to scrape per board.
        keywords: Comma-separated filter keywords.
        today: If True, only include articles posted today.
        from_date: Start date for date range filter (YYYY-MM-DD).
        to_date: End date for date range filter (YYYY-MM-DD).

    Returns:
        None. Outputs results to data/ directory.
    """
    # Parse date strings
    parsed_from = None
    parsed_to = None
    try:
        if from_date:
            parsed_from = datetime.strptime(from_date, "%Y-%m-%d").date()
        if to_date:
            parsed_to = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        logger.error("날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        raise typer.Exit(code=1)

    if parsed_from and parsed_to and parsed_from > parsed_to:
        logger.error("--from 날짜가 --to 날짜보다 이후입니다.")
        raise typer.Exit(code=1)

    keyword_list = (
        [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if keywords
        else [settings.keyword]
    )
    asyncio.run(_scrape(headed, pages, keyword_list, today, parsed_from, parsed_to))


async def _scrape(
    headed: bool,
    pages: int | None,
    keywords: list[str],
    today_only: bool,
    from_date: date | None = None,
    to_date: date | None = None,
) -> None:
    """Async scraping pipeline."""
    from playwright.async_api import async_playwright
    from src.auth import cookies_exist, create_authenticated_context
    from src.exporter import export_csv
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
    # --from/--to takes precedence over --today
    use_date_range = from_date is not None or to_date is not None

    if use_date_range:
        fr = from_date.isoformat() if from_date else "처음"
        to = to_date.isoformat() if to_date else "오늘"
        logger.info(f"기간 필터: {fr} ~ {to}")
    elif today_only:
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

            # Debug: show sample timestamp values
            if all_articles:
                sample = all_articles[0]
                logger.debug(
                    f"[샘플] title={sample.title[:30]}, "
                    f"timestamp={sample.write_timestamp}, "
                    f"write_date='{sample.write_date}'"
                )

            # Filter by date range or today
            if use_date_range:
                all_articles = _filter_date_range(
                    all_articles, from_date, to_date
                )
                logger.info(
                    f"기간 필터 적용 후: {len(all_articles)}건"
                )
                if not all_articles:
                    logger.warning("해당 기간에 올라온 공고가 없습니다.")
                    raise typer.Exit(code=0)
            elif today_only:
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
            today_str = date.today().strftime("%Y-%m-%d")
            csv_path = DATA_DIR / f"{today_str}.csv"
            export_csv(postings, csv_path)

        finally:
            await context.browser.close()

    logger.success("스크래핑 완료!")


def _filter_today(
    articles: list,
) -> list:
    """Filter articles to only include those posted today.

    Args:
        articles: List of ArticleSummary objects.

    Returns:
        Filtered list containing only today's articles.
    """
    kst = timezone(timedelta(hours=9))
    today_kst = datetime.now(kst).date()

    filtered = []
    for article in articles:
        article_date = _parse_article_date(article, kst, today_kst)
        if article_date == today_kst:
            filtered.append(article)

    return filtered


def _filter_date_range(
    articles: list,
    from_date: date | None,
    to_date: date | None,
) -> list:
    """Filter articles to only include those within a date range.

    Args:
        articles: List of ArticleSummary objects.
        from_date: Start date (inclusive). None means no lower bound.
        to_date: End date (inclusive). None means today.

    Returns:
        Filtered list containing only articles within the range.
    """
    import re

    kst = timezone(timedelta(hours=9))
    today_kst = datetime.now(kst).date()

    if to_date is None:
        to_date = today_kst

    filtered = []
    for article in articles:
        article_date = _parse_article_date(article, kst, today_kst)
        if article_date is None:
            # 날짜를 알 수 없는 경우 포함 (누락 방지)
            filtered.append(article)
            continue

        if from_date and article_date < from_date:
            continue
        if article_date > to_date:
            continue

        filtered.append(article)

    return filtered


def _parse_article_date(
    article: object,
    kst: timezone,
    today_kst: date,
) -> date | None:
    """Extract date from an article using timestamp or text fallback.

    Tries epoch milliseconds first, then epoch seconds, with a
    sanity check (year 2020-2030). Falls back to write_date text.

    Args:
        article: ArticleSummary object.
        kst: KST timezone.
        today_kst: Today's date in KST.

    Returns:
        Parsed date, or None if unparseable.
    """
    import re

    # Method 1: Use timestamp if available
    if article.write_timestamp > 0:
        ts = article.write_timestamp

        # Try epoch milliseconds
        try:
            d = datetime.fromtimestamp(ts / 1000, tz=kst).date()
            if 2020 <= d.year <= 2030:
                return d
        except (OSError, OverflowError, ValueError):
            pass

        # Try epoch seconds
        try:
            d = datetime.fromtimestamp(ts, tz=kst).date()
            if 2020 <= d.year <= 2030:
                return d
        except (OSError, OverflowError, ValueError):
            pass

        logger.debug(
            f"timestamp 해석 실패: {ts} (article_id={article.article_id})"
        )

    # Method 2: Parse write_date text
    wd = article.write_date
    if not wd:
        return None

    # "2026.03.01." or "2026.03.01"
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", wd)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # "03.01." (no year → current year)
    m = re.match(r"^(\d{2})\.(\d{2})\.?$", wd)
    if m:
        return date(today_kst.year, int(m.group(1)), int(m.group(2)))

    # Time-only formats → today
    if re.match(r"^\d{1,2}:\d{2}$", wd):
        return today_kst
    if "분 전" in wd or "시간 전" in wd or "방금" in wd:
        return today_kst

    return None


if __name__ == "__main__":
    app()
