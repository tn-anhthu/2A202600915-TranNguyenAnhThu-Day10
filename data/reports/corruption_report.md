# Phase 2 — Corruption & Repair Report

_Generated: 2026-06-10 09:17 UTC_

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
| `null_rate_paper_id` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_title` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_summary` | ❌ FAIL | 19.0% null/empty (threshold 0%) |
| `null_rate_published` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_abs_url` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_authors_joined` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `all_key_fields_complete_rate` | ❌ FAIL | 81.0% rows have all key fields (threshold 90%) |
| `doi_format_valid_rate` | ✅ PASS | 100.0% paper_ids match DOI pattern (threshold 90%) |
| `abs_url_http_rate` | ✅ PASS | 100.0% abs_urls have http/https schema (threshold 90%) |
| `published_not_future_rate` | ✅ PASS | 100.0% published dates are not in the future (threshold 90%) |
| `summary_min_words` | ❌ FAIL | min 0 words in summary (threshold 10) |
| `date_format_consistent` | ✅ PASS | 100.0% non-empty published dates match YYYY-MM-DD (threshold 95%) |
| `summary_no_residual_xml` | ✅ PASS | 100.0% summaries are XML-tag-free (threshold 95%) |
| `abs_url_doi_consistent_rate` | ✅ PASS | 100.0% DOI paper_ids have consistent abs_url (threshold 80%) |
| `stale_row_rate` | ❌ FAIL | 9.5% rows older than 180 days (2/21 stale) |
| `max_age_days` | ❌ FAIL | max age = 2557 days (threshold 180) |
| `mean_age_days` | ❌ FAIL | mean age = 344.4 days (threshold 180) |
| `last_updated_timestamp` | ✅ PASS | most recent updated = 2026-05-20 |
| `doi_regex_valid_rate` | ✅ PASS | 100.0% paper_ids match DOI regex (threshold 90%) |
| `abs_url_schema_valid` | ✅ PASS | 100.0% abs_url have valid http/https schema (threshold 90%) |
| `pdf_url_schema_valid` | ✅ PASS | 100.0% pdf_url have valid http/https schema (threshold 90%) |
| `published_date_range_valid` | ✅ PASS | 100.0% published dates in [2000-01-01, today] (threshold 90%) |
| `summary_chars_range_valid` | ❌ FAIL | 81.0% summaries in [20, 50000] chars; min=0, max=2506 |
| `paper_id_unique_rate` | ❌ FAIL | 90.5% unique paper_ids; 2 duplicate(s) |
| `title_unique_rate` | ❌ FAIL | 90.5% unique titles; 2 duplicate(s) |
| `dedup_rate` | ❌ FAIL | dedup rate = 90.48% (threshold 99%) |

**Overall:** ❌ Some checks failed (21 rows)

### Repaired Dataset

| Check | Status | Detail |
|-------|--------|--------|
| `row_count` | ✅ PASS | 23 rows (min 4) |
| `null_rate_paper_id` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_title` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_summary` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_published` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_abs_url` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `null_rate_authors_joined` | ✅ PASS | 0.0% null/empty (threshold 0%) |
| `all_key_fields_complete_rate` | ✅ PASS | 100.0% rows have all key fields (threshold 90%) |
| `doi_format_valid_rate` | ✅ PASS | 100.0% paper_ids match DOI pattern (threshold 90%) |
| `abs_url_http_rate` | ✅ PASS | 100.0% abs_urls have http/https schema (threshold 90%) |
| `published_not_future_rate` | ✅ PASS | 100.0% published dates are not in the future (threshold 90%) |
| `summary_min_words` | ✅ PASS | min 132 words in summary (threshold 10) |
| `date_format_consistent` | ✅ PASS | 100.0% non-empty published dates match YYYY-MM-DD (threshold 95%) |
| `summary_no_residual_xml` | ✅ PASS | 100.0% summaries are XML-tag-free (threshold 95%) |
| `abs_url_doi_consistent_rate` | ✅ PASS | 100.0% DOI paper_ids have consistent abs_url (threshold 80%) |
| `stale_row_rate` | ✅ PASS | 0.0% rows older than 180 days (0/23 stale) |
| `max_age_days` | ✅ PASS | max age = 173 days (threshold 180) |
| `mean_age_days` | ✅ PASS | mean age = 106.0 days (threshold 180) |
| `last_updated_timestamp` | ✅ PASS | most recent updated = 2026-06-02 |
| `doi_regex_valid_rate` | ✅ PASS | 100.0% paper_ids match DOI regex (threshold 90%) |
| `abs_url_schema_valid` | ✅ PASS | 100.0% abs_url have valid http/https schema (threshold 90%) |
| `pdf_url_schema_valid` | ✅ PASS | 100.0% pdf_url have valid http/https schema (threshold 90%) |
| `published_date_range_valid` | ✅ PASS | 100.0% published dates in [2000-01-01, today] (threshold 90%) |
| `summary_chars_range_valid` | ✅ PASS | 100.0% summaries in [20, 50000] chars; min=1037, max=2506 |
| `paper_id_unique_rate` | ✅ PASS | 100.0% unique paper_ids; 0 duplicate(s) |
| `title_unique_rate` | ✅ PASS | 100.0% unique titles; 0 duplicate(s) |
| `dedup_rate` | ✅ PASS | dedup rate = 100.00% (threshold 99%) |

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
