"""Application configuration using Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"


class Settings(BaseSettings):
    """Scraper configuration loaded from environment variables and .env file.

    Args:
        cafe_id: Naver cafe URL slug (e.g. 'studentstudyhard').
        keyword: Keyword to filter job postings (default: '전산').
        scrape_pages: Number of listing pages to scrape per board.
        request_delay: Seconds to wait between HTTP requests.
        headless: Run Playwright browser in headless mode.
        cookies_path: Path to saved browser cookies JSON.
        output_md: Path for Markdown output file.
        output_csv: Path for CSV output file.

    Returns:
        Settings instance with validated configuration values.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cafe_id: str = "studentstudyhard"
    keyword: str = "전산"
    scrape_pages: int = 2
    request_delay: float = 1.0
    headless: bool = True

    # Target board names (display names from cafe menu)
    target_boards: list[str] = [
        "★중앙공기업",
        "★지방공기업",
        "★대학/기타기관",
    ]

    @property
    def cookies_path(self) -> Path:
        """Path to the saved cookies JSON file."""
        return DATA_DIR / "cookies.json"

    @property
    def output_md(self) -> Path:
        """Path for Markdown results output."""
        return DATA_DIR / "results.md"

    @property
    def output_csv(self) -> Path:
        """Path for CSV results output."""
        return DATA_DIR / "results.csv"

    @property
    def cafe_url(self) -> str:
        """Full Naver cafe URL."""
        return f"https://cafe.naver.com/{self.cafe_id}"


settings = Settings()
