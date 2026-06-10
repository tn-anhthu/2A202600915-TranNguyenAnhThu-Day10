from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

# Reproducible corruption with a fixed seed
_SEED = 42
_DROP_FRACTION = 0.20     # drop 20% of newest records
_BLANK_FRACTION = 0.20    # blank summary on 20% of remaining rows
_NOISE_FRACTION = 0.20    # inject noise into summary on 20%
_TRUNCATE_FRACTION = 0.20 # truncate title to 20 chars on 20%
_STALE_FRACTION = 0.15    # make 15% of dates stale (> 2 years old)
_STALE_DATE = "2019-01-01"
_DUP_COUNT = 2            # duplicate 2 rows

_NOISE_TOKEN = "xΩ∅ [CORRUPTED_DATA] %&# NaN null undefined"


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Abstract: {row['summary']}\n"
        f"Authors: {row.get('authors_joined', '')}\n"
        f"Categories: {row.get('categories_joined', '')}"
    ).strip()


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhiều dạng data corruption.

    1. Drop một số latest records (newest rows, sorted by published desc).
    2. Blank summary ở một số dòng.
    3. Inject noise vào summary.
    4. Làm title bị truncate.
    5. Làm published date cũ đi (stale).
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vào output_log_path.
    """
    rng = random.Random(_SEED)
    corrupted = df.copy()
    log: list[dict[str, Any]] = []
    n0 = len(corrupted)

    # --- 1. Drop latest records ---
    # df is sorted newest-first; drop from the top
    n_drop = max(1, int(n0 * _DROP_FRACTION))
    drop_ids = list(corrupted.iloc[:n_drop]["paper_id"])
    corrupted = corrupted.iloc[n_drop:].reset_index(drop=True)
    log.append({
        "type": "drop_latest",
        "affected": n_drop,
        "detail": f"Dropped {n_drop} newest records",
        "paper_ids": drop_ids,
    })

    # --- 2. Blank summary ---
    n_blank = max(1, int(len(corrupted) * _BLANK_FRACTION))
    blank_indices = rng.sample(list(corrupted.index), n_blank)
    corrupted.loc[blank_indices, "summary"] = ""
    corrupted.loc[blank_indices, "summary_chars"] = 0
    log.append({
        "type": "blank_summary",
        "affected": n_blank,
        "detail": f"Blanked summary on {n_blank} rows",
        "indices": blank_indices,
    })

    # --- 3. Inject noise into summary ---
    remaining = [i for i in corrupted.index if i not in blank_indices]
    n_noise = max(1, int(len(corrupted) * _NOISE_FRACTION))
    noise_indices = rng.sample(remaining, min(n_noise, len(remaining)))
    for i in noise_indices:
        corrupted.at[i, "summary"] = _NOISE_TOKEN + " " + corrupted.at[i, "summary"]
        corrupted.at[i, "summary_chars"] = len(corrupted.at[i, "summary"])
    log.append({
        "type": "noise_injection",
        "affected": len(noise_indices),
        "detail": f"Injected noise token into {len(noise_indices)} summaries",
        "indices": noise_indices,
    })

    # --- 4. Truncate title ---
    n_trunc = max(1, int(len(corrupted) * _TRUNCATE_FRACTION))
    trunc_indices = rng.sample(list(corrupted.index), n_trunc)
    for i in trunc_indices:
        corrupted.at[i, "title"] = corrupted.at[i, "title"][:20]
    log.append({
        "type": "title_truncate",
        "affected": n_trunc,
        "detail": f"Truncated titles to 20 chars on {n_trunc} rows",
        "indices": trunc_indices,
    })

    # --- 5. Stale publication date ---
    n_stale = max(1, int(len(corrupted) * _STALE_FRACTION))
    stale_indices = rng.sample(list(corrupted.index), n_stale)
    for i in stale_indices:
        corrupted.at[i, "published"] = _STALE_DATE
        # age_days for stale date: roughly 7+ years
        corrupted.at[i, "age_days"] = 2557
    log.append({
        "type": "stale_date",
        "affected": n_stale,
        "detail": f"Set published date to {_STALE_DATE} on {n_stale} rows",
        "indices": stale_indices,
    })

    # --- 6. Add duplicate rows ---
    dup_source = corrupted.iloc[:_DUP_COUNT].copy()
    corrupted = pd.concat([corrupted, dup_source], ignore_index=True)
    log.append({
        "type": "add_duplicates",
        "affected": _DUP_COUNT,
        "detail": f"Added {_DUP_COUNT} duplicate rows",
        "paper_ids": list(dup_source["paper_id"]),
    })

    # --- 7. Rebuild text_for_embedding ---
    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text_for_embedding, axis=1)

    # --- 8. Write corruption log ---
    corruption_log: dict[str, Any] = {
        "seed": _SEED,
        "total_before": n0,
        "total_after": len(corrupted),
        "corruptions": log,
    }
    out = Path(output_log_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corruption_log, indent=2, ensure_ascii=True), encoding="utf-8")

    return corrupted
