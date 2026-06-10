from __future__ import annotations

import json
from typing import Any

import pandas as pd

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tạo bộ data quality checks và ghi kết quả vào data/quality/.

    1. Check row count.
    2. Check paper_id not null và unique.
    3. Check title not null.
    4. Check độ dài summary.
    5. Check freshness bằng age_days.
    6. Ghi kết quả vào data/quality/<report_name>_quality.json.
    """
    checks: list[dict[str, Any]] = []
    n = len(df)

    # 1. Row count
    min_rows = 4
    checks.append({
        "name": "row_count",
        "passed": n >= min_rows,
        "detail": f"{n} rows (min {min_rows})",
    })

    # 2. paper_id not null
    null_ids = int(df["paper_id"].isna().sum()) + int((df["paper_id"].fillna("") == "").sum())
    checks.append({
        "name": "paper_id_not_null",
        "passed": null_ids == 0,
        "detail": f"{null_ids} null or empty paper_id values",
    })

    # 3. paper_id unique
    dup_count = n - df["paper_id"].nunique()
    checks.append({
        "name": "paper_id_unique",
        "passed": dup_count == 0,
        "detail": f"{dup_count} duplicate paper_id values",
    })

    # 4. title not null
    null_titles = int(df["title"].isna().sum()) + int((df["title"].fillna("") == "").sum())
    checks.append({
        "name": "title_not_null",
        "passed": null_titles == 0,
        "detail": f"{null_titles} null or empty titles",
    })

    # 5. summary length
    if "summary_chars" in df.columns:
        min_chars = int(df["summary_chars"].min())
    else:
        min_chars = int(df["summary"].fillna("").str.len().min())
    min_threshold = 20
    checks.append({
        "name": "summary_length",
        "passed": min_chars >= min_threshold,
        "detail": f"min {min_chars} chars (threshold {min_threshold})",
    })

    # 6. freshness via age_days
    if "age_days" in df.columns:
        threshold = settings.freshness_threshold_days
        stale = int((df["age_days"].fillna(0) > threshold).sum())
        checks.append({
            "name": "freshness",
            "passed": stale == 0,
            "detail": f"{stale}/{n} rows older than {threshold} days",
        })

    overall = all(c["passed"] for c in checks)
    result: dict[str, Any] = {
        "report_name": report_name,
        "total_rows": n,
        "passed": overall,
        "checks": checks,
    }

    out_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")

    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tổng hợp freshness report và ghi JSON.

    1. Tìm latest và oldest published date.
    2. Đếm số dòng stale (age_days > freshness_threshold_days).
    3. Tạo payload: latest_published, oldest_published, stale_rows, total_rows, is_fresh.
    4. Ghi JSON report.
    """
    from pathlib import Path

    pub = df["published"].replace("", None).dropna()
    latest_published = str(pub.max()) if len(pub) else ""
    oldest_published = str(pub.min()) if len(pub) else ""

    threshold = settings.freshness_threshold_days
    stale_rows = int((df["age_days"].fillna(0) > threshold).sum()) if "age_days" in df.columns else 0
    total_rows = len(df)

    payload: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": stale_rows == 0,
        "freshness_threshold_days": threshold,
    }

    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    return payload
