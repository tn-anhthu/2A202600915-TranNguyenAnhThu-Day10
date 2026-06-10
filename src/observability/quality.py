from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

import pandas as pd

from core.config import Settings

# Regex patterns for Validity / Accuracy
_DOI_RE   = re.compile(r"^10\.\d{4,9}/\S+$")
_HTTP_RE  = re.compile(r"^https?://", re.IGNORECASE)
_DATE_RE  = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_XML_RE   = re.compile(r"<[^>]+>")

_KEY_FIELDS = ["paper_id", "title", "summary", "published", "abs_url", "authors_joined"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def _rate(series: pd.Series) -> float:
    """Return the fraction of True values (0-1)."""
    return float(series.mean()) if len(series) else 1.0


def _dim(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(c["passed"] for c in checks)
    score  = sum(c["passed"] for c in checks) / len(checks) if checks else 1.0
    return {"passed": passed, "score": round(score, 3), "checks": checks}


# ── 6 dimensions ─────────────────────────────────────────────────────────────

def _completeness(df: pd.DataFrame) -> dict[str, Any]:
    """Không thiếu records/fields quan trọng."""
    checks: list[dict[str, Any]] = []
    n = len(df)

    # Row count
    checks.append(_check("row_count", n >= 4, f"{n} rows (min 4)"))

    # % NULL per key field
    null_rates: dict[str, float] = {}
    for field in _KEY_FIELDS:
        if field not in df.columns:
            null_rates[field] = 1.0
            continue
        null_count = int(df[field].isna().sum()) + int((df[field].fillna("") == "").sum())
        null_rate = null_count / n if n else 0.0
        null_rates[field] = null_rate

    for field, rate in null_rates.items():
        checks.append(_check(
            f"null_rate_{field}",
            rate == 0.0,
            f"{rate*100:.1f}% null/empty (threshold 0%)",
        ))

    # All key fields complete rate (all non-null in the same row)
    mask = pd.Series([True] * n, index=df.index)
    for field in _KEY_FIELDS:
        if field in df.columns:
            mask &= df[field].fillna("").astype(str).str.len() > 0
    complete_rate = float(mask.mean()) if n else 1.0
    checks.append(_check(
        "all_key_fields_complete_rate",
        complete_rate >= 0.90,
        f"{complete_rate*100:.1f}% rows have all key fields (threshold 90%)",
    ))

    return _dim(checks)


def _accuracy(df: pd.DataFrame) -> dict[str, Any]:
    """Data đúng với thực tế và business rules."""
    checks: list[dict[str, Any]] = []
    n = len(df)
    today_str = date.today().isoformat()

    # DOI format (paper_id should match 10.xxxx/...)
    doi_rate = _rate(df["paper_id"].fillna("").apply(lambda x: bool(_DOI_RE.match(x))))
    checks.append(_check(
        "doi_format_valid_rate",
        doi_rate >= 0.90,
        f"{doi_rate*100:.1f}% paper_ids match DOI pattern (threshold 90%)",
    ))

    # abs_url must start with http
    url_rate = _rate(df["abs_url"].fillna("").apply(lambda x: bool(_HTTP_RE.match(x))))
    checks.append(_check(
        "abs_url_http_rate",
        url_rate >= 0.90,
        f"{url_rate*100:.1f}% abs_urls have http/https schema (threshold 90%)",
    ))

    # Published date must not be in the future
    def _not_future(d: str) -> bool:
        try:
            return bool(d) and d <= today_str
        except Exception:
            return False

    future_rate = _rate(df["published"].fillna("").apply(lambda x: _not_future(str(x))))
    checks.append(_check(
        "published_not_future_rate",
        future_rate >= 0.90,
        f"{future_rate*100:.1f}% published dates are not in the future (threshold 90%)",
    ))

    # Summary must contain substantive text (>= 10 words)
    word_counts = df["summary"].fillna("").str.split().str.len()
    min_words = int(word_counts.min()) if n else 0
    checks.append(_check(
        "summary_min_words",
        min_words >= 10,
        f"min {min_words} words in summary (threshold 10)",
    ))

    return _dim(checks)


def _consistency(df: pd.DataFrame) -> dict[str, Any]:
    """Cùng entity, cùng format across fields."""
    checks: list[dict[str, Any]] = []

    # Date format: non-empty published must be YYYY-MM-DD
    non_empty_pub = df["published"].fillna("").replace("", None).dropna()
    if len(non_empty_pub):
        date_fmt_rate = _rate(non_empty_pub.apply(lambda x: bool(_DATE_RE.match(str(x)))))
    else:
        date_fmt_rate = 1.0
    checks.append(_check(
        "date_format_consistent",
        date_fmt_rate >= 0.95,
        f"{date_fmt_rate*100:.1f}% non-empty published dates match YYYY-MM-DD (threshold 95%)",
    ))

    # No residual XML/JATS tags in summary
    xml_free_rate = _rate(df["summary"].fillna("").apply(lambda x: not bool(_XML_RE.search(x))))
    checks.append(_check(
        "summary_no_residual_xml",
        xml_free_rate >= 0.95,
        f"{xml_free_rate*100:.1f}% summaries are XML-tag-free (threshold 95%)",
    ))

    # abs_url and paper_id consistency: if paper_id is a DOI, abs_url should contain the DOI
    def _url_doi_consistent(row: pd.Series) -> bool:
        pid = str(row.get("paper_id", ""))
        url = str(row.get("abs_url", ""))
        if not _DOI_RE.match(pid):
            return True  # not a DOI; skip
        return pid.lower() in url.lower() or "doi.org" in url.lower()

    consist_rate = _rate(df.apply(_url_doi_consistent, axis=1))
    checks.append(_check(
        "abs_url_doi_consistent_rate",
        consist_rate >= 0.80,
        f"{consist_rate*100:.1f}% DOI paper_ids have consistent abs_url (threshold 80%)",
    ))

    return _dim(checks)


def _timeliness(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Data đủ fresh cho use case."""
    checks: list[dict[str, Any]] = []
    n = len(df)
    threshold = settings.freshness_threshold_days

    if "age_days" in df.columns:
        age = df["age_days"].fillna(0)
        stale_count = int((age > threshold).sum())
        stale_rate  = stale_count / n if n else 0.0
        max_age     = int(age.max())
        mean_age    = float(age.mean())

        checks.append(_check(
            "stale_row_rate",
            stale_rate == 0.0,
            f"{stale_rate*100:.1f}% rows older than {threshold} days ({stale_count}/{n} stale)",
        ))
        checks.append(_check(
            "max_age_days",
            max_age <= threshold,
            f"max age = {max_age} days (threshold {threshold})",
        ))
        checks.append(_check(
            "mean_age_days",
            mean_age <= threshold,
            f"mean age = {mean_age:.1f} days (threshold {threshold})",
        ))
    else:
        checks.append(_check("age_days_available", False, "age_days column missing"))

    # last-updated timestamp: most recent `updated` field
    if "updated" in df.columns:
        recent = df["updated"].replace("", None).dropna()
        last_updated = str(recent.max()) if len(recent) else "N/A"
        checks.append(_check(
            "last_updated_timestamp",
            last_updated != "N/A",
            f"most recent updated = {last_updated}",
        ))

    return _dim(checks)


def _validity(df: pd.DataFrame) -> dict[str, Any]:
    """Đúng format và domain rules."""
    checks: list[dict[str, Any]] = []
    today_str = date.today().isoformat()

    # DOI regex validity (same as accuracy but here checks format strictly)
    doi_valid = _rate(df["paper_id"].fillna("").apply(lambda x: bool(_DOI_RE.match(x))))
    checks.append(_check(
        "doi_regex_valid_rate",
        doi_valid >= 0.90,
        f"{doi_valid*100:.1f}% paper_ids match DOI regex (threshold 90%)",
    ))

    # URL schema (http or https only)
    for col in ["abs_url", "pdf_url"]:
        if col in df.columns:
            rate = _rate(df[col].fillna("").apply(lambda x: bool(_HTTP_RE.match(x)) if x else True))
            checks.append(_check(
                f"{col}_schema_valid",
                rate >= 0.90,
                f"{rate*100:.1f}% {col} have valid http/https schema (threshold 90%)",
            ))

    # Published date range: [2000-01-01, today]
    def _in_range(d: str) -> bool:
        if not d:
            return True
        return "2000-01-01" <= str(d) <= today_str

    date_range_rate = _rate(df["published"].fillna("").apply(_in_range))
    checks.append(_check(
        "published_date_range_valid",
        date_range_rate >= 0.90,
        f"{date_range_rate*100:.1f}% published dates in [2000-01-01, today] (threshold 90%)",
    ))

    # Summary chars range [20, 50000]
    if "summary_chars" in df.columns:
        chars = df["summary_chars"].fillna(0)
        min_c, max_c = int(chars.min()), int(chars.max())
        in_range_rate = _rate((chars >= 20) & (chars <= 50000))
        checks.append(_check(
            "summary_chars_range_valid",
            in_range_rate >= 0.90,
            f"{in_range_rate*100:.1f}% summaries in [20, 50000] chars; min={min_c}, max={max_c}",
        ))

    return _dim(checks)


def _uniqueness(df: pd.DataFrame) -> dict[str, Any]:
    """Không có duplicates."""
    checks: list[dict[str, Any]] = []
    n = len(df)

    # paper_id uniqueness
    n_unique_id = df["paper_id"].nunique()
    dup_count   = n - n_unique_id
    id_rate     = n_unique_id / n if n else 1.0
    checks.append(_check(
        "paper_id_unique_rate",
        dup_count == 0,
        f"{id_rate*100:.1f}% unique paper_ids; {dup_count} duplicate(s)",
    ))

    # title uniqueness
    n_unique_title = df["title"].nunique()
    title_dup      = n - n_unique_title
    title_rate     = n_unique_title / n if n else 1.0
    checks.append(_check(
        "title_unique_rate",
        title_rate >= 0.95,
        f"{title_rate*100:.1f}% unique titles; {title_dup} duplicate(s)",
    ))

    # dedup rate (1 = no duplicates)
    dedup_rate = 1.0 - (dup_count / n if n else 0.0)
    checks.append(_check(
        "dedup_rate",
        dedup_rate >= 0.99,
        f"dedup rate = {dedup_rate*100:.2f}% (threshold 99%)",
    ))

    return _dim(checks)


# ── public API ────────────────────────────────────────────────────────────────

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tạo bộ data quality checks đầy đủ 6 chiều và ghi kết quả vào data/quality/.

    Dimensions:
      1. Completeness  — % NULL per field, row count vs expected
      2. Accuracy      — DOI format, URL schema, date not-future, word count
      3. Consistency   — date format, no residual XML, url-doi alignment
      4. Timeliness    — max/mean age_days, stale rate, last-updated timestamp
      5. Validity      — regex patterns, range checks (date, summary_chars, url)
      6. Uniqueness    — paper_id dedup rate, title dedup rate
    """
    dims: dict[str, Any] = {
        "completeness": _completeness(df),
        "accuracy":     _accuracy(df),
        "consistency":  _consistency(df),
        "timeliness":   _timeliness(df, settings),
        "validity":     _validity(df),
        "uniqueness":   _uniqueness(df),
    }

    # Flat checks list (backward-compatible)
    flat: list[dict[str, Any]] = []
    for dim_name, dim_data in dims.items():
        for c in dim_data["checks"]:
            flat.append({**c, "dimension": dim_name})

    overall = all(d["passed"] for d in dims.values())
    result: dict[str, Any] = {
        "report_name": report_name,
        "total_rows":  len(df),
        "passed":      overall,
        "dimensions":  dims,
        "checks":      flat,   # backward compat
    }

    out_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")

    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tổng hợp freshness report và ghi JSON."""
    from pathlib import Path

    pub = df["published"].replace("", None).dropna()
    latest_published  = str(pub.max()) if len(pub) else ""
    oldest_published  = str(pub.min()) if len(pub) else ""

    threshold  = settings.freshness_threshold_days
    stale_rows = int((df["age_days"].fillna(0) > threshold).sum()) if "age_days" in df.columns else 0
    total_rows = len(df)

    payload: dict[str, Any] = {
        "latest_published":        latest_published,
        "oldest_published":        oldest_published,
        "stale_rows":              stale_rows,
        "total_rows":              total_rows,
        "is_fresh":                stale_rows == 0,
        "freshness_threshold_days": threshold,
    }

    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    return payload
