"""Scrape article detail pages to extract job posting information."""

import asyncio
import re

from loguru import logger
from playwright.async_api import BrowserContext

from src.config import settings
from src.models import ArticleSummary, JobPosting


async def scrape_article_details(
    context: BrowserContext,
    articles: list[ArticleSummary],
) -> list[JobPosting]:
    """Visit each article page and extract institution name and deadline.

    Navigates to each article URL, switches to the cafe_main iframe,
    and parses the article body for structured job information.

    Args:
        context: Authenticated Playwright BrowserContext.
        articles: List of ArticleSummary to fetch details for.

    Returns:
        List of JobPosting objects with extracted detail fields.
    """
    postings: list[JobPosting] = []
    page = await context.new_page()

    try:
        for i, article in enumerate(articles, 1):
            logger.info(
                f"[{i}/{len(articles)}] 상세 조회: {article.title}"
            )

            try:
                posting = await _extract_single(page, article)
                postings.append(posting)
            except Exception as e:
                logger.warning(
                    f"게시글 상세 추출 실패 (ID: {article.article_id}): {e}"
                )
                postings.append(
                    JobPosting(
                        category=article.board_category,
                        title=article.title,
                        link=article.link,
                    )
                )

            await asyncio.sleep(settings.request_delay)

    finally:
        await page.close()

    return postings


async def _extract_single(
    page: object, article: ArticleSummary
) -> JobPosting:
    """Extract job posting details from a single article page.

    Args:
        page: Playwright Page object (reused across articles).
        article: ArticleSummary with the URL to visit.

    Returns:
        JobPosting with extracted institution, deadline, etc.
    """
    await page.goto(article.link, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # Switch to cafe_main iframe
    frame = page.frame("cafe_main")
    if not frame:
        iframe_el = await page.query_selector("iframe#cafe_main")
        if iframe_el:
            frame = await iframe_el.content_frame()

    if not frame:
        logger.warning("cafe_main iframe을 찾을 수 없습니다.")
        return JobPosting(
            category=article.board_category,
            title=article.title,
            link=article.link,
        )

    # Get article body text
    body_text = await _get_body_text(frame)

    # Extract fields
    institution = _extract_institution(body_text, article.title)
    deadline = _extract_deadline_from_title(article.title)

    return JobPosting(
        category=article.board_category,
        institution=institution,
        title=article.title,
        deadline=deadline,
        link=article.link,
    )


async def _get_body_text(frame: object) -> str:
    """Extract article body text from the iframe.

    Args:
        frame: Playwright Frame containing the article content.

    Returns:
        Plain text content of the article body.
    """
    selectors = [
        ".se-main-container",
        ".ContentRenderer",
        "#body",
        ".article_viewer",
        ".content_area",
        "#postContent",
    ]

    for selector in selectors:
        element = await frame.query_selector(selector)
        if element:
            text = await element.inner_text()
            if text.strip():
                return text.strip()

    # Fallback: get entire frame text
    return await frame.inner_text("body")


def _extract_institution(body_text: str, title: str) -> str:
    """Extract institution name from article body or title.

    Uses heuristic patterns common in Korean job postings.

    Args:
        body_text: Full text content of the article.
        title: Article title string.

    Returns:
        Institution name or '확인필요' if not found.
    """
    # Pattern 1: Common institution patterns in body
    patterns = [
        r"기관[명\s]*[:：]\s*(.+?)(?:\n|$)",
        r"채용기관[명\s]*[:：]\s*(.+?)(?:\n|$)",
        r"회사[명\s]*[:：]\s*(.+?)(?:\n|$)",
        r"공사[명\s]*[:：]\s*(.+?)(?:\n|$)",
        r"공단[명\s]*[:：]\s*(.+?)(?:\n|$)",
        r"기관\s*[:：]\s*(.+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, body_text)
        if match:
            name = match.group(1).strip()
            if 2 <= len(name) <= 30:
                return name

    # Pattern 2: Extract from title
    # Common title formats: "[기관명] 공고명" or "기관명 - 공고명"
    title_patterns = [
        r"\[([^\]]+)\]",
        r"^(.+?)\s*[-–—]\s*",
        r"^(.+?)\s+(?:채용|모집|공개|정규)",
    ]

    for pattern in title_patterns:
        match = re.search(pattern, title)
        if match:
            name = match.group(1).strip()
            # Remove trailing " 채용" suffix
            name = re.sub(r"\s*채용$", "", name)
            if 2 <= len(name) <= 20:
                return name

    return "확인필요"


def _extract_deadline_from_title(title: str) -> str:
    """Extract deadline from the trailing (~X.XX) pattern in the title.

    Args:
        title: Article title string, e.g. '... (전산) (~3.4)'.

    Returns:
        Deadline string without parentheses, e.g. '~3.4'.
    """
    match = re.search(r"\((\~\d+\.\d+)\)\s*$", title)
    if match:
        return match.group(1)
    return "확인필요"


def _extract_deadline(body_text: str) -> str:
    """Extract application deadline from article body text.

    Args:
        body_text: Full text content of the article.

    Returns:
        Deadline string or '확인필요' if not found.
    """
    # Pattern 1: Labeled deadline
    label_patterns = [
        r"(?:접수|마감|원서접수|지원)\s*(?:기간|기한|마감|일시)?\s*[:：]\s*(.+?)(?:\n|$)",
        r"(?:접수마감|마감일|응시원서)\s*[:：]?\s*(.+?)(?:\n|$)",
        r"(?:~|～)\s*(20\d{2}[.\-/]\s*\d{1,2}[.\-/]\s*\d{1,2}[^)\n]*)",
    ]

    for pattern in label_patterns:
        match = re.search(pattern, body_text)
        if match:
            deadline = match.group(1).strip()
            # Validate it looks like a date
            if re.search(r"\d{4}[.\-/]\s*\d{1,2}", deadline):
                return _clean_deadline(deadline)

    # Pattern 2: Date near deadline keywords
    date_pattern = r"(20\d{2}[.\-/\s]*\d{1,2}[.\-/\s]*\d{1,2}(?:[^)\n]{0,20})?)"
    keyword_area = re.split(
        r"(?:접수|마감|원서)", body_text, flags=re.IGNORECASE
    )

    for section in keyword_area[1:]:
        match = re.search(date_pattern, section[:200])
        if match:
            return _clean_deadline(match.group(1).strip())

    # Pattern 3: Any date in the document as last resort
    all_dates = re.findall(
        r"20\d{2}[.\-/]\s*\d{1,2}[.\-/]\s*\d{1,2}", body_text
    )
    if all_dates:
        # Return the last date (likely the deadline)
        return _clean_deadline(all_dates[-1])

    return "확인필요"


def _clean_deadline(raw: str) -> str:
    """Clean and normalize a deadline string.

    Args:
        raw: Raw deadline text with possible extra characters.

    Returns:
        Cleaned deadline string.
    """
    # Remove extra whitespace
    cleaned = re.sub(r"\s+", " ", raw).strip()
    # Truncate at reasonable length
    if len(cleaned) > 50:
        cleaned = cleaned[:50].rsplit(" ", 1)[0]
    return cleaned
