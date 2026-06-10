from __future__ import annotations

from datetime import datetime

from core.config import load_settings
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Baseline pipeline end-to-end.

    1. Load settings.
    2. Load hoặc fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tạo hoặc load evaluation set.
    7. Evaluate.
    8. Run quality checks và freshness report.
    9. Tạo markdown report.
    10. Demo agent trên vài sample question.
    """
    # 1. Load settings
    settings = load_settings()
    print(f"[phase1] provider={settings.llm_provider}  model={settings.model_name}")

    # 2. Load or fetch raw records
    raw_exists = settings.paths.raw_records_json.exists()
    if settings.refresh_source or not raw_exists:
        print("[phase1] Fetching raw records from Crossref API...")
        records = fetch_source_records(settings)
    else:
        print(f"[phase1] Loading cached raw records from {settings.paths.raw_records_json.name}")
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"[phase1] Raw records: {len(records)}")

    # 3. Clean data
    print("[phase1] Cleaning data...")
    df = build_clean_dataframe(records, datetime.now())
    print(f"[phase1] Clean records: {len(df)}")

    # 4. Save clean CSV / JSON
    write_csv(df, settings.paths.clean_csv)
    df.to_json(str(settings.paths.clean_json), orient="records", force_ascii=False, indent=2)
    print(f"[phase1] Saved → {settings.paths.clean_csv.name}  {settings.paths.clean_json.name}")

    # 5. Build Chroma embedding index
    print("[phase1] Building embedding index (this may take a moment)...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print("[phase1] Embedding index ready.")

    # 6. Create or load evaluation test set
    test_exists = settings.paths.eval_testset.exists()
    if settings.refresh_test_set or not test_exists:
        print("[phase1] Building evaluation test set...")
        build_test_set(df, settings.paths.eval_testset)
    else:
        print(f"[phase1] Using existing test set: {settings.paths.eval_testset.name}")

    # 7. Evaluate pipeline
    print("[phase1] Evaluating pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    m = bundle.summary
    print(
        f"[phase1] hit_rate={m['retrieval_hit_rate']:.2f}  "
        f"token_f1={m['mean_token_f1']:.2f}  "
        f"judge_acc={m['judge_accuracy']:.2f}  "
        f"judge_score={m['mean_judge_score']:.2f}/5"
    )

    # 8. Data quality checks + freshness report
    print("[phase1] Running data quality checks...")
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    q_status = "PASSED" if quality["passed"] else "FAILED"
    f_status = "fresh" if freshness["is_fresh"] else "stale"
    print(f"[phase1] Quality: {q_status}  Freshness: {f_status}")

    # 9. Generate markdown report
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"[phase1] Report → {settings.paths.baseline_report}")

    # 10. Demo agent on sample questions (no LLM required — rule-based qa)
    print("\n[phase1] === Agent Demo ===")
    first_title = df.iloc[0]["title"]
    demo_questions = [
        f"What is the paper '{first_title}' about?",
        f"Who authored the paper '{first_title}'?",
        f"When was '{first_title}' published?",
    ]
    demo_answers = []
    for q in demo_questions:
        result = answer_question(q, settings=settings, index=index)
        print(f"  Q: {q[:72]}")
        print(f"  A: {result.answer[:100]}")
        print()
        demo_answers.append({"question": q, "answer": result.answer})
    write_json(settings.paths.demo_answers, demo_answers)

    print("[phase1] Done. Artifacts written to data/")
