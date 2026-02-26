"""Export job postings to Markdown table and CSV formats."""

from pathlib import Path

import pandas as pd
from loguru import logger

from src.models import JobPosting


def export_results(
    postings: list[JobPosting],
    md_path: Path,
    csv_path: Path,
) -> None:
    """Export job postings to both Markdown and CSV files.

    Args:
        postings: List of JobPosting objects to export.
        md_path: Output path for the Markdown file.
        csv_path: Output path for the CSV file.

    Returns:
        None. Writes files to the specified paths.
    """
    if not postings:
        logger.warning("내보낼 공고가 없습니다.")
        return

    df = _to_dataframe(postings)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    _export_markdown(df, md_path)
    _export_csv(df, csv_path)

    logger.success(f"결과 저장 완료: {len(postings)}건")
    logger.info(f"  Markdown: {md_path}")
    logger.info(f"  CSV: {csv_path}")


def _to_dataframe(postings: list[JobPosting]) -> pd.DataFrame:
    """Convert job postings to a pandas DataFrame.

    Args:
        postings: List of JobPosting objects.

    Returns:
        DataFrame with Korean column headers.
    """
    rows = []
    for p in postings:
        rows.append({
            "기관분류": p.category,
            "기관명": p.institution,
            "공고명": p.title,
            "접수기한": p.deadline,
            "링크": p.link,
        })

    return pd.DataFrame(rows)


def _export_markdown(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame as a Markdown table with clickable links.

    Args:
        df: DataFrame with job posting data.
        path: Output file path.

    Returns:
        None. Writes the Markdown file.
    """
    lines = [
        "# 전산직 채용공고 스크래핑 결과\n",
        f"총 {len(df)}건\n",
    ]

    # Header
    headers = ["기관분류", "기관명", "공고명", "접수기한", "링크"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # Rows
    for _, row in df.iterrows():
        cells = [
            str(row["기관분류"]),
            str(row["기관명"]),
            str(row["공고명"]),
            str(row["접수기한"]),
            str(row["링크"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _export_csv(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame as a CSV file.

    Args:
        df: DataFrame with job posting data.
        path: Output file path.

    Returns:
        None. Writes the CSV file.
    """
    df.to_csv(path, index=False, encoding="utf-8-sig")


def export_txt(
    postings: list[JobPosting],
    txt_path: Path,
    *,
    title: str = "",
) -> None:
    """Export job postings as a formatted text table.

    Args:
        postings: List of JobPosting objects to export.
        txt_path: Output path for the text file.
        title: Optional title header for the file.

    Returns:
        None. Writes the text file.
    """
    if not postings:
        logger.warning("내보낼 공고가 없습니다.")
        return

    txt_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate column widths
    headers = ["No", "기관분류", "기관명", "공고명", "접수기한", "링크"]
    rows: list[list[str]] = []
    for i, p in enumerate(postings, 1):
        rows.append([
            str(i),
            p.category,
            p.institution,
            p.title,
            p.deadline,
            p.link,
        ])

    widths = [len(h) for h in headers]
    for row in rows:
        for j, cell in enumerate(row):
            # Approximate display width (Korean chars = 2)
            display_w = sum(2 if ord(c) > 127 else 1 for c in cell)
            widths[j] = max(widths[j], display_w)

    def _pad(text: str, width: int) -> str:
        """Pad text to target display width."""
        display_w = sum(2 if ord(c) > 127 else 1 for c in text)
        return text + " " * (width - display_w)

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_line = "|" + "|".join(
        f" {_pad(h, widths[i])} " for i, h in enumerate(headers)
    ) + "|"

    lines: list[str] = []
    if title:
        lines.append(title)
        lines.append("")

    lines.append(f"총 {len(postings)}건")
    lines.append("")
    lines.append(sep)
    lines.append(header_line)
    lines.append(sep)

    for row in rows:
        row_line = "|" + "|".join(
            f" {_pad(cell, widths[j])} " for j, cell in enumerate(row)
        ) + "|"
        lines.append(row_line)

    lines.append(sep)
    lines.append("")

    txt_path.write_text("\n".join(lines), encoding="utf-8")
    logger.success(f"TXT 저장: {txt_path}")
    logger.info(f"  {len(postings)}건 저장됨")
