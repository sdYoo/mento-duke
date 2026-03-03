"""Export job postings to a dated CSV file."""

from pathlib import Path

import pandas as pd
from loguru import logger

from src.models import JobPosting


def export_csv(
    postings: list[JobPosting],
    csv_path: Path,
) -> None:
    """Export job postings to a CSV file.

    Overwrites the file if it already exists (same-day re-runs).

    Args:
        postings: List of JobPosting objects to export.
        csv_path: Output path for the CSV file.

    Returns:
        None. Writes the CSV file.
    """
    if not postings:
        logger.warning("내보낼 공고가 없습니다.")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for p in postings:
        rows.append({
            "기관분류": p.category,
            "기관명": p.institution,
            "공고명": p.title,
            "접수기한": p.deadline,
            "링크": p.link,
        })

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    logger.success(f"CSV 저장: {csv_path}")
    logger.info(f"  {len(postings)}건 저장됨")
