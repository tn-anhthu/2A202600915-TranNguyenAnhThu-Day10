# Phase 2 — Corruption & Repair Report

_Generated: 2026-06-10 06:45 UTC_

---

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Δ Corrupt | Repaired | Δ Repair vs Baseline |
|--------|----------|-----------|-----------|----------|----------------------|
| Retrieval Hit Rate | 100.0% | 75.0% | ▼ -0.250 | 100.0% | → +0.000 |
| Mean Token F1 | 1.000 | 0.705 | ▼ -0.295 | 1.000 | → +0.000 |
| Judge Accuracy | 100.0% | 70.8% | ▼ -0.292 | 100.0% | → +0.000 |
| Mean Judge Score (/5) | 5.000 | 3.667 | ▼ -1.333 | 5.000 | → +0.000 |

---

## 2. Data Quality

### Corrupted Dataset

| Check | Status | Detail |
|-------|--------|--------|
| `row_count` | ✅ PASS | 21 rows (min 4) |
| `paper_id_not_null` | ✅ PASS | 0 null or empty paper_id values |
| `paper_id_unique` | ❌ FAIL | 2 duplicate paper_id values |
| `title_not_null` | ✅ PASS | 0 null or empty titles |
| `summary_length` | ❌ FAIL | min 0 chars (threshold 20) |
| `freshness` | ❌ FAIL | 2/21 rows older than 180 days |

**Overall:** ❌ Some checks failed (21 rows)

### Repaired Dataset

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

## 3. Data Freshness

| Field | Corrupted | Repaired |
|-------|-----------|----------|
| Latest published | 2026-05-06 | 2026-06-02 |
| Oldest published | 2019-01-01 | 2025-12-19 |
| Stale rows | 2/21 | 0/23 |
| Is fresh | ❌ | ✅ |

---

## 4. Analysis

### Impact of Corruption

- Retrieval hit rate dropped by **25.0%** after corruption (100.0% → 75.0%).
- Mean Token F1 dropped by **29.5%** after corruption (1.000 → 0.705).

### Recovery after Repair

- Retrieval hit rate recovered to **100.0%** (baseline 100.0%, 100% of gap recovered).
- Mean Token F1 recovered to **1.000** (baseline 1.000, 100% of gap recovered).
