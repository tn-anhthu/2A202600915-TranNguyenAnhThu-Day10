from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def _fmt_score(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.3f}"


def _quality_table(quality: dict[str, Any]) -> str:
    lines = [
        "| Check | Status | Detail |",
        "|-------|--------|--------|",
    ]
    for c in quality.get("checks", []):
        status = "✅ PASS" if c["passed"] else "❌ FAIL"
        lines.append(f"| `{c['name']}` | {status} | {c['detail']} |")
    overall = "✅ All checks passed" if quality.get("passed") else "❌ Some checks failed"
    lines.append(f"\n**Overall:** {overall} ({quality.get('total_rows', 0)} rows)")
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viết markdown report cho baseline phase.

    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality và freshness.
    4. Ghi markdown vào report_path.
    """
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# Phase 1 — Baseline Pipeline Report",
        "",
        f"_Generated: {ts}_",
        "",
        "---",
        "",
        "## 1. Data Source",
        "",
        f"- **API:** {source_summary.get('source_api', 'Crossref REST API')}",
        f"- **Query:** `{source_summary.get('query', '')}`",
        f"- **Filter:** `{source_summary.get('filter', '')}`",
        f"- **Raw records fetched:** {source_summary.get('raw_records', 'N/A')}",
        f"- **Records after cleaning:** {source_summary.get('clean_records', 'N/A')}",
        "",
        "---",
        "",
        "## 2. Evaluation Metrics (Baseline)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Samples evaluated | {metrics.get('samples', 'N/A')} |",
        f"| Retrieval Hit Rate | {_fmt_pct(metrics.get('retrieval_hit_rate'))} |",
        f"| Mean Token F1 | {_fmt_score(metrics.get('mean_token_f1'))} |",
        f"| Judge Accuracy | {_fmt_pct(metrics.get('judge_accuracy'))} |",
        f"| Mean Judge Score | {_fmt_score(metrics.get('mean_judge_score'))} / 5 |",
        "",
    ]

    ragas = metrics.get("ragas")
    if ragas and not ragas.get("skipped") and not ragas.get("error"):
        lines += [
            "### RAGAS Scores",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ]
        for k, v in ragas.items():
            lines.append(f"| {k} | {_fmt_score(v) if isinstance(v, float) else v} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## 3. Data Quality",
        "",
        _quality_table(quality),
        "",
        "---",
        "",
        "## 4. Data Freshness",
        "",
        f"- **Latest published:** {freshness.get('latest_published', 'N/A')}",
        f"- **Oldest published:** {freshness.get('oldest_published', 'N/A')}",
        f"- **Stale rows (> {freshness.get('freshness_threshold_days', 180)} days):**"
        f" {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}",
        f"- **Freshness status:** {'✅ Fresh' if freshness.get('is_fresh') else '⚠️ Stale data detected'}",
        "",
    ]

    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viết markdown report so sánh baseline / corrupted / repaired."""

    def _delta(base: float | None, after: float | None) -> str:
        if base is None or after is None:
            return "N/A"
        diff = after - base
        arrow = "▲" if diff > 0.001 else ("▼" if diff < -0.001 else "→")
        return f"{arrow} {diff:+.3f}"

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# Phase 2 — Corruption & Repair Report",
        "",
        f"_Generated: {ts}_",
        "",
        "---",
        "",
        "## 1. Metrics Comparison",
        "",
        "| Metric | Baseline | Corrupted | Δ Corrupt | Repaired | Δ Repair vs Baseline |",
        "|--------|----------|-----------|-----------|----------|----------------------|",
    ]

    metric_rows = [
        ("Retrieval Hit Rate", "retrieval_hit_rate", _fmt_pct),
        ("Mean Token F1", "mean_token_f1", _fmt_score),
        ("Judge Accuracy", "judge_accuracy", _fmt_pct),
        ("Mean Judge Score (/5)", "mean_judge_score", _fmt_score),
    ]
    for label, key, fmt in metric_rows:
        base = baseline_metrics.get(key)
        corr = corrupted_metrics.get(key)
        rep = repaired_metrics.get(key)
        lines.append(
            f"| {label} | {fmt(base)} | {fmt(corr)} | {_delta(base, corr)}"
            f" | {fmt(rep)} | {_delta(base, rep)} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 2. Data Quality",
        "",
        "### Corrupted Dataset",
        "",
        _quality_table(corrupted_quality),
        "",
        "### Repaired Dataset",
        "",
        _quality_table(repaired_quality),
        "",
        "---",
        "",
        "## 3. Data Freshness",
        "",
        "| Field | Corrupted | Repaired |",
        "|-------|-----------|----------|",
        f"| Latest published | {corrupted_freshness.get('latest_published', 'N/A')}"
        f" | {repaired_freshness.get('latest_published', 'N/A')} |",
        f"| Oldest published | {corrupted_freshness.get('oldest_published', 'N/A')}"
        f" | {repaired_freshness.get('oldest_published', 'N/A')} |",
        f"| Stale rows | {corrupted_freshness.get('stale_rows', 0)}/{corrupted_freshness.get('total_rows', 0)}"
        f" | {repaired_freshness.get('stale_rows', 0)}/{repaired_freshness.get('total_rows', 0)} |",
        f"| Is fresh | {'✅' if corrupted_freshness.get('is_fresh') else '❌'}"
        f" | {'✅' if repaired_freshness.get('is_fresh') else '❌'} |",
        "",
        "---",
        "",
        "## 4. Analysis",
        "",
        "### Impact of Corruption",
        "",
    ]

    rhr_base = baseline_metrics.get("retrieval_hit_rate") or 0.0
    rhr_corr = corrupted_metrics.get("retrieval_hit_rate") or 0.0
    rhr_rep = repaired_metrics.get("retrieval_hit_rate") or 0.0
    f1_base = baseline_metrics.get("mean_token_f1") or 0.0
    f1_corr = corrupted_metrics.get("mean_token_f1") or 0.0
    f1_rep = repaired_metrics.get("mean_token_f1") or 0.0

    if rhr_base:
        drop = (rhr_base - rhr_corr) / rhr_base * 100
        lines.append(f"- Retrieval hit rate dropped by **{drop:.1f}%** after corruption "
                     f"({_fmt_pct(rhr_base)} → {_fmt_pct(rhr_corr)}).")
    if f1_base:
        drop = (f1_base - f1_corr) / f1_base * 100
        lines.append(f"- Mean Token F1 dropped by **{drop:.1f}%** after corruption "
                     f"({_fmt_score(f1_base)} → {_fmt_score(f1_corr)}).")

    lines += ["", "### Recovery after Repair", ""]

    if rhr_base:
        gap = rhr_base - rhr_corr
        recovery = ((rhr_rep - rhr_corr) / gap * 100) if gap != 0 else 100.0
        lines.append(f"- Retrieval hit rate recovered to **{_fmt_pct(rhr_rep)}** "
                     f"(baseline {_fmt_pct(rhr_base)}, {recovery:.0f}% of gap recovered).")
    if f1_base:
        gap = f1_base - f1_corr
        recovery = ((f1_rep - f1_corr) / gap * 100) if gap != 0 else 100.0
        lines.append(f"- Mean Token F1 recovered to **{_fmt_score(f1_rep)}** "
                     f"(baseline {_fmt_score(f1_base)}, {recovery:.0f}% of gap recovered).")

    lines.append("")

    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
