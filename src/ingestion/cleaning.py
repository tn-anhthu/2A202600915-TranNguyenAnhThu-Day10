from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord

_MIN_TITLE_LEN = 5
_MIN_SUMMARY_CHARS = 20


_ABSTRACT_PREFIX = re.compile(r"^Abstract\.?\s*", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _normalize_summary(text: str) -> str:
    return _normalize_text(_ABSTRACT_PREFIX.sub("", text.strip()))


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành dataframe sẵn sàng để embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tính age_days.
    4. Tạo cột helper: authors_joined, categories_joined, summary_chars, text_for_embedding.
    5. Drop duplicates và filter row xấu.
    6. Sort dataframe và return.
    """
    run_dt = run_date.replace(tzinfo=None)
    rows = []

    for r in records:
        # --- 1. Normalize core text fields ---
        title = _normalize_text(r.title)
        summary = _normalize_summary(r.summary)

        if not title or not summary:
            continue

        authors = [_normalize_text(a) for a in r.authors if a.strip()]
        categories = [_normalize_text(c) for c in r.categories if c.strip()]
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        primary_category = _normalize_text(r.primary_category)

        # --- 2. Parse dates ---
        published = r.published
        updated = r.updated
        pub_dt = _parse_date(published)
        upd_dt = _parse_date(updated)

        # Keep canonical ISO string; fall back to raw value if parse fails
        published_iso = pub_dt.strftime("%Y-%m-%d") if pub_dt else published
        updated_iso = upd_dt.strftime("%Y-%m-%d") if upd_dt else updated

        # --- 3. Compute age_days ---
        age_days: int | None = (run_dt - pub_dt).days if pub_dt else None

        # --- 4. Helper columns ---
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Abstract: {summary}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}"
        ).strip()

        rows.append(
            {
                "paper_id": r.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_iso,
                "updated": updated_iso,
                "age_days": age_days,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # --- 5. Drop duplicates and filter bad rows ---
    df = df.drop_duplicates(subset=["paper_id"])
    df = df.drop_duplicates(subset=["title"])
    df = df[df["title"].str.len() >= _MIN_TITLE_LEN]
    df = df[df["summary_chars"] >= _MIN_SUMMARY_CHARS]

    # --- 6. Sort newest-first, stable by paper_id ---
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df
