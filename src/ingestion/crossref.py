from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings

CROSSREF_API_URL = "https://api.crossref.org/works"
_MAX_RETRIES = 3
_RETRY_BACKOFF = [2, 5, 10]


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _extract_date(item: dict, *keys: str) -> str:
    for key in keys:
        date_obj = item.get(key)
        if date_obj and "date-parts" in date_obj:
            parts = date_obj["date-parts"][0]
            if parts and parts[0]:
                year = parts[0]
                month = parts[1] if len(parts) > 1 else 1
                day = parts[2] if len(parts) > 2 else 1
                return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    1. Duyệt `payload["message"]["items"]`.
    2. Lấy DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuẩn hoá text và bỏ record không hợp lệ (thiếu DOI, title, hoặc abstract).
    4. Trả về list `PaperRecord`.
    """
    records: list[PaperRecord] = []
    items = payload.get("message", {}).get("items", [])

    for item in items:
        # --- paper_id: DOI ---
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        # --- title ---
        title_list = item.get("title", [])
        title = title_list[0].strip() if title_list else ""
        if not title:
            continue

        # --- summary / abstract (strip JATS XML tags) ---
        raw_abstract = item.get("abstract", "").strip()
        summary = re.sub(r"<[^>]+>", " ", raw_abstract).strip()
        summary = re.sub(r"\s+", " ", summary)
        if not summary:
            continue

        # --- authors ---
        authors: list[str] = []
        for a in item.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            if family:
                authors.append(f"{given} {family}".strip() if given else family)

        # --- categories / subjects ---
        categories: list[str] = item.get("subject", [])
        primary_category = categories[0] if categories else ""

        # --- dates ---
        published = _extract_date(item, "published", "published-print", "published-online", "issued")
        updated = _extract_date(item, "deposited", "indexed")

        # --- URLs ---
        abs_url = item.get("URL") or f"https://doi.org/{doi}"
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break
        if not pdf_url:
            pdf_url = f"https://doi.org/{doi}"

        comment = item.get("note", "")

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi Crossref API, lưu raw response, parse thành records.

    1. Tạo params từ `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Gọi API với retry cho các status code 429/503.
    3. Lưu raw response vào `settings.paths.raw_api_response`.
    4. Parse payload bằng `parse_crossref_payload`.
    5. Lưu records vào `settings.paths.raw_records_json`.
    """
    params: dict = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "mailto": "student@vinai.io",  # polite pool → higher rate limit
    }

    response: requests.Response | None = None
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(CROSSREF_API_URL, params=params, timeout=30)
            if resp.status_code in (429, 503):
                wait = _RETRY_BACKOFF[min(attempt, len(_RETRY_BACKOFF) - 1)]
                time.sleep(wait)
                continue
            resp.raise_for_status()
            response = resp
            break
        except requests.RequestException as exc:
            last_exc = exc
            wait = _RETRY_BACKOFF[min(attempt, len(_RETRY_BACKOFF) - 1)]
            if attempt < _MAX_RETRIES - 1:
                time.sleep(wait)

    if response is None:
        raise RuntimeError(
            f"Failed to fetch Crossref API after {_MAX_RETRIES} attempts."
        ) from last_exc

    payload = response.json()

    # Save raw API response
    raw_path: Path = settings.paths.raw_api_response
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Parse and save records
    records = parse_crossref_payload(payload)

    records_path: Path = settings.paths.raw_records_json
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(
        json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot và map thành `PaperRecord`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in data]
