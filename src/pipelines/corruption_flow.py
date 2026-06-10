from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corruption → evaluate → repair → compare flow.

    1. Load baseline metrics và clean dataset.
    2. Tạo corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index và evaluate trên corrupted data.
    5. Run quality checks / freshness trên corrupted data.
    6. Repair lại từ raw records.
    7. Evaluate repaired dataset.
    8. Tạo comparison report.
    """
    # 1. Load settings + baseline artifacts
    settings = load_settings()
    print(f"[corruption_flow] provider={settings.llm_provider}  model={settings.model_name}")

    print("[corruption_flow] Loading baseline metrics and clean dataset...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    df_baseline = pd.read_csv(settings.paths.clean_csv)
    print(f"[corruption_flow] Baseline: {len(df_baseline)} rows, "
          f"hit_rate={baseline_metrics['retrieval_hit_rate']:.2f}")

    # 2. Create corrupted dataframe
    print("[corruption_flow] Corrupting dataset...")
    df_corrupted = corrupt_clean_dataframe(df_baseline, settings.paths.corruption_log)
    corruption_log = read_json(settings.paths.corruption_log)
    print(
        f"[corruption_flow] Corrupted: {corruption_log['total_before']} → "
        f"{corruption_log['total_after']} rows — "
        + ", ".join(f"{c['type']}({c['affected']})" for c in corruption_log["corruptions"])
    )

    # 3. Save corrupted artifacts
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    df_corrupted.to_json(
        str(settings.paths.corrupted_clean_json), orient="records", force_ascii=False, indent=2
    )
    print(f"[corruption_flow] Saved → {settings.paths.corrupted_clean_csv.name}")

    # 4. Rebuild index on corrupted data + evaluate
    print("[corruption_flow] Building corrupted embedding index...")
    index_corrupted = LocalEmbeddingIndex.build(
        df_corrupted, settings, settings.paths.corrupted_embeddings_json
    )
    print("[corruption_flow] Evaluating corrupted pipeline...")
    bundle_corrupted = evaluate_pipeline(
        settings=settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    mc = bundle_corrupted.summary
    print(
        f"[corruption_flow] Corrupted metrics → "
        f"hit_rate={mc['retrieval_hit_rate']:.2f}  "
        f"token_f1={mc['mean_token_f1']:.2f}  "
        f"judge_acc={mc['judge_accuracy']:.2f}"
    )

    # 5. Quality checks + freshness on corrupted data
    print("[corruption_flow] Quality checks on corrupted data...")
    quality_corrupted = run_data_quality_checks(df_corrupted, settings, "corrupted")
    freshness_corrupted = build_freshness_report(
        df_corrupted, settings, settings.paths.quality_dir / "freshness_corrupted.json"
    )
    q_status = "PASSED" if quality_corrupted["passed"] else "FAILED"
    print(f"[corruption_flow] Quality: {q_status}  "
          f"Freshness: {'fresh' if freshness_corrupted['is_fresh'] else 'stale'}")

    # 6. Repair: re-clean from original raw records
    print("[corruption_flow] Repairing from raw records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, datetime.now())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    df_repaired.to_json(
        str(settings.paths.repaired_clean_json), orient="records", force_ascii=False, indent=2
    )
    print(f"[corruption_flow] Repaired: {len(df_repaired)} rows → "
          f"{settings.paths.repaired_clean_csv.name}")

    # 7. Evaluate repaired dataset
    print("[corruption_flow] Building repaired embedding index...")
    index_repaired = LocalEmbeddingIndex.build(
        df_repaired, settings, settings.paths.repaired_embeddings_json
    )
    print("[corruption_flow] Evaluating repaired pipeline...")
    bundle_repaired = evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    mr = bundle_repaired.summary
    print(
        f"[corruption_flow] Repaired metrics → "
        f"hit_rate={mr['retrieval_hit_rate']:.2f}  "
        f"token_f1={mr['mean_token_f1']:.2f}  "
        f"judge_acc={mr['judge_accuracy']:.2f}"
    )

    # 8. Quality checks + freshness on repaired data
    quality_repaired = run_data_quality_checks(df_repaired, settings, "repaired")
    freshness_repaired = build_freshness_report(
        df_repaired, settings, settings.paths.quality_dir / "freshness_repaired.json"
    )

    # 9. Generate comparison report
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=bundle_corrupted.summary,
        repaired_metrics=bundle_repaired.summary,
        corrupted_quality=quality_corrupted,
        repaired_quality=quality_repaired,
        corrupted_freshness=freshness_corrupted,
        repaired_freshness=freshness_repaired,
    )
    print(f"[corruption_flow] Report → {settings.paths.comparison_report}")

    # Print final comparison summary
    print("\n[corruption_flow] === Metrics Comparison ===")
    print(f"  {'Metric':<22} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}")
    print(f"  {'-'*22} {'-'*10} {'-'*10} {'-'*10}")
    for key, label in [
        ("retrieval_hit_rate", "Hit Rate"),
        ("mean_token_f1", "Token F1"),
        ("judge_accuracy", "Judge Acc"),
        ("mean_judge_score", "Judge Score"),
    ]:
        b = baseline_metrics.get(key, 0)
        c = mc.get(key, 0)
        r = mr.get(key, 0)
        print(f"  {label:<22} {b:>10.3f} {c:>10.3f} {r:>10.3f}")

    print("\n[corruption_flow] Done.")
