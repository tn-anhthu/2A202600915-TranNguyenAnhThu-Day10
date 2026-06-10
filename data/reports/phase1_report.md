# Phase 1 — Baseline Pipeline Report

_Generated: 2026-06-10 06:38 UTC_

---

## 1. Data Source

- **API:** Crossref REST API
- **Query:** `agentic retrieval augmented generation large language model`
- **Filter:** `from-pub-date:2025-12-12,has-abstract:true`
- **Raw records fetched:** 23
- **Records after cleaning:** 23

---

## 2. Evaluation Metrics (Baseline)

| Metric | Value |
|--------|-------|
| Samples evaluated | 24 |
| Retrieval Hit Rate | 100.0% |
| Mean Token F1 | 1.000 |
| Judge Accuracy | 100.0% |
| Mean Judge Score | 5.000 / 5 |

---

## 3. Data Quality

| Check | Status | Detail |
|-------|--------|--------|
| `row_count` | ✅ PASS | 23 rows (min 4) |
| `paper_id_not_null` | ✅ PASS | 0 null or empty paper_id values |
| `paper_id_unique` | ✅ PASS | 0 duplicate paper_id values |
| `title_not_null` | ✅ PASS | 0 null or empty titles |
| `summary_length` | ✅ PASS | min 1037 chars (threshold 20) |
| `freshness` | ✅ PASS | 0/23 rows older than 180 days |

**Overall:** ✅ All checks passed (23 rows)

---

## 4. Data Freshness

- **Latest published:** 2026-06-02
- **Oldest published:** 2025-12-19
- **Stale rows (> 180 days):** 0 / 23
- **Freshness status:** ✅ Fresh
