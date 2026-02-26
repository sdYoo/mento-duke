"""Data models for the Naver Cafe scraper."""

from pydantic import BaseModel, Field


class Board(BaseModel):
    """Represents a cafe menu board (게시판).

    Args:
        menu_id: Naver cafe internal menu ID.
        menu_name: Display name of the board.
        club_id: Naver cafe internal club ID.
        category: Cleaned category label (e.g. '중앙공기업').
    """

    menu_id: int
    menu_name: str
    club_id: int
    category: str = ""


class ArticleSummary(BaseModel):
    """Summary of a single article from the listing page.

    Args:
        article_id: Unique article identifier.
        title: Article title text.
        board_category: Which board this article belongs to.
        writer: Author display name.
        write_date: Date string as returned by the API.
        link: Direct URL to the article.
    """

    article_id: int
    title: str
    board_category: str = ""
    writer: str = ""
    write_date: str = ""
    write_timestamp: int = 0
    link: str = ""


class JobPosting(BaseModel):
    """Extracted job posting with detail fields.

    Args:
        category: Board category (e.g. '중앙공기업', '지방공기업').
        institution: Hiring institution name.
        title: Job posting title.
        deadline: Application deadline string.
        link: Direct URL to the posting.
    """

    category: str = ""
    institution: str = Field(default="확인필요")
    title: str = ""
    deadline: str = Field(default="확인필요")
    link: str = ""
