from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

_MIN_DOCS = 4
_SELECT_N = 8  # papers to sample across the sorted dataframe


def _evenly_spaced(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Pick n rows spread evenly across the dataframe (covers full date range)."""
    if len(df) <= n:
        return df
    step = len(df) / n
    indices = [int(i * step) for i in range(n)]
    return df.iloc[indices]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tạo bộ evaluation set từ cleaned dataframe.

    1. Kiểm tra số lượng document tối thiểu.
    2. Chọn một số paper đại diện trải đều theo date range.
    3. Tạo nhiều loại câu hỏi per paper:
       - summary   : "What is the paper '<title>' about?"
       - authors   : "Who authored the paper '<title>'?"
       - date      : "When was '<title>' published?"
       - categories: "What categories does '<title>' belong to?"
    4. Mỗi row: id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Ghi file JSON vào output_path.

    Question templates phải khớp với keyword logic của qa.py._extract_answer:
      - 'who authored'  → metadata['authors_joined']
      - 'when was'      → metadata['published']
      - 'what categories' → metadata['categories_joined']
      - fallback        → first_sentence(metadata['summary'])
    """
    if len(df) < _MIN_DOCS:
        raise ValueError(f"Need at least {_MIN_DOCS} documents to build a test set, got {len(df)}.")

    selected = _evenly_spaced(df, _SELECT_N)
    samples: list[dict[str, Any]] = []
    counter = 0

    for _, row in selected.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors_joined = str(row.get("authors_joined") or "")
        categories_joined = str(row.get("categories_joined") or "")
        published = str(row.get("published") or "")

        # --- summary: fallback branch in _extract_answer ---
        gt_summary = first_sentence(summary)
        if gt_summary:
            counter += 1
            samples.append(
                {
                    "id": f"q{counter:03d}",
                    "question_type": "summary",
                    "question": f"What is the paper '{title}' about?",
                    "ground_truth": gt_summary,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        # --- authors: triggers "who authored" branch ---
        if authors_joined:
            counter += 1
            samples.append(
                {
                    "id": f"q{counter:03d}",
                    "question_type": "authors",
                    "question": f"Who authored the paper '{title}'?",
                    "ground_truth": authors_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        # --- date: triggers "when was" branch ---
        if published:
            counter += 1
            samples.append(
                {
                    "id": f"q{counter:03d}",
                    "question_type": "date",
                    "question": f"When was '{title}' published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        # --- categories: triggers "what categories" branch ---
        if categories_joined:
            counter += 1
            samples.append(
                {
                    "id": f"q{counter:03d}",
                    "question_type": "categories",
                    "question": f"What categories does '{title}' belong to?",
                    "ground_truth": categories_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(output_path, samples)
    return samples
