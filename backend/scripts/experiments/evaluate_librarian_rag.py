"""Evaluación del pipeline Librarian/RAG (Experimento A).

Evalúa localmente el pipeline real:
user query -> Librarian query -> SQL filter -> vector search -> metadata-aware reranker.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:
    yaml = None

try:
    import matplotlib.pyplot as plt
    import numpy as np
except Exception:
    plt = None
    np = None

_script_path = Path(__file__).resolve()
_backend_app = _script_path.parents[2] / "app"
if str(_backend_app) not in sys.path:
    sys.path.insert(0, str(_backend_app))

LOG = logging.getLogger("evaluate_librarian_rag")
logging.basicConfig(level=logging.INFO)


@dataclass
class EvalCase:
    id: str
    user_query: str
    athlete_context: dict
    expected: dict


def load_eval_cases(path: str | None = None) -> list[EvalCase]:
    if path and yaml:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [EvalCase(**d) for d in data]

    repo_yaml = _script_path.parents[3] / "evaluation" / "librarian_rag_eval_queries.yaml"
    if not repo_yaml.exists():
        repo_yaml = _script_path.parents[1] / "evaluation" / "librarian_rag_eval_queries.yaml"
    if not repo_yaml.exists():
        repo_yaml = Path.cwd() / "evaluation" / "librarian_rag_eval_queries.yaml"

    if repo_yaml.exists() and yaml:
        with open(repo_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [EvalCase(**d) for d in data]

    raise RuntimeError("No queries available. Install pyyaml or provide --queries-file")


def map_tsb_category(cat: str | None) -> float | None:
    mapping = {
        "very_fatigued": -25.0,
        "fatigued": -12.0,
        "normal": 0.0,
        "fresh": 12.0,
        "very_fresh": 20.0,
    }
    return mapping.get(cat) if cat else None


def build_full_athlete_context(minimal_context: dict) -> dict:
    from datetime import date, timedelta

    full_ctx = {**minimal_context}
    defaults = {
        "ftp": 275,
        "weight": 75.0,
        "w_per_kg": 3.67,
        "age": 35,
        "max_hr": 185,
        "goal": "improve_endurance",
        "available_days": 5,
        "next_event_name": None,
        "next_event_date": None,
        "next_event_days": None,
        "ctl": 55.0,
        "atl": 30.0,
        "km_avg_4w": 200.0,
        "hours_avg_4w": 12.0,
        "tss_avg_4w": 800.0,
        "last_training_date": (date.today() - timedelta(days=1)).isoformat(),
        "last_training_name": "Easy ride",
        "last_training_tss": 120.0,
        "last_training_type": "endurance",
        "done_this_week": 3,
        "tss_week": 600,
        "planned_this_week": [],
        "blocked_this_week": [],
        "wellness_days_available": 0,
    }
    for key, value in defaults.items():
        full_ctx.setdefault(key, value)

    if "tsb" not in full_ctx and "tsb_category" in full_ctx:
        full_ctx["tsb"] = map_tsb_category(full_ctx.get("tsb_category"))
    if full_ctx.get("tsb") is None:
        full_ctx["tsb"] = 0.0

    return full_ctx


def expected_matches(field: str, actual: Any, expected: dict) -> bool:
    if f"{field}_any_of" in expected:
        return actual in expected[f"{field}_any_of"]
    if field in expected:
        return actual == expected[field]
    return True


def compute_relevance_grade(template: dict[str, Any], expected: dict[str, Any]) -> int:
    title = (template.get("title") or "").upper()
    prefixes = expected.get("relevant_title_prefixes") or []
    if any(title.startswith(prefix.upper()) for prefix in prefixes):
        return 3

    if not expected_matches("primary_goal", template.get("primary_goal"), expected):
        family_pairs = {
            ("sweetspot", "threshold"),
            ("threshold", "sweetspot"),
            ("tempo", "endurance"),
            ("endurance", "tempo"),
            ("strength_torque", "neuromuscular_sprint"),
            ("neuromuscular_sprint", "strength_torque"),
        }
        exp_goals = expected.get("primary_goal_any_of") or [expected.get("primary_goal")]
        actual_goal = template.get("primary_goal")
        if actual_goal and any((actual_goal, exp_goal) in family_pairs for exp_goal in exp_goals if exp_goal):
            return 1
        return 0

    wz_ok = expected_matches("work_zone", template.get("work_zone"), expected)
    st_ok = expected_matches("structure_type", template.get("structure_type"), expected)
    fatigue_ok = expected_matches("fatigue_suitability", template.get("fatigue_suitability"), expected)
    duration_ok = expected_matches("duration_class", template.get("duration_class"), expected)

    if wz_ok and st_ok and fatigue_ok and duration_ok:
        return 3
    if (wz_ok or st_ok) and fatigue_ok:
        return 2
    return 1


def precision_at_k(rels: list[int], k: int) -> float:
    if k <= 0:
        return 0.0
    topk = rels[:k]
    return sum(1 for rel in topk if rel >= 2) / k


def hit_at_k(rels: list[int], k: int) -> int:
    return 1 if any(rel >= 2 for rel in rels[:k]) else 0


def mrr(rels: list[int], k: int) -> float:
    for idx, rel in enumerate(rels[:k], start=1):
        if rel >= 2:
            return 1.0 / idx
    return 0.0


def dcg(rels: list[int], k: int) -> float:
    score = 0.0
    for idx, rel in enumerate(rels[:k], start=1):
        score += (2 ** rel - 1) / math.log2(idx + 1)
    return score


def ndcg(rels: list[int], k: int) -> float:
    ideal = dcg(sorted(rels, reverse=True), k)
    if ideal == 0:
        return 0.0
    return dcg(rels, k) / ideal


def label_check(key: str, generated_labels: dict, expected: dict) -> int | None:
    gen = generated_labels.get(key)
    if gen is None:
        return None
    if f"{key}_any_of" in expected:
        return 1 if gen in expected[f"{key}_any_of"] else 0
    if key in expected:
        return 1 if gen == expected[key] else 0
    return None


def _mean_skip_none(values: list[int | float | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return statistics.mean(filtered)


def infer_failure_reason(trace: dict) -> str:
    metrics = trace.get("metrics", {})
    expected = trace.get("expected", {})
    generated = trace.get("generated_semantic_labels", {})

    if "primary_goal" in expected and generated.get("primary_goal") != expected["primary_goal"]:
        return "bad_librarian_query"
    if "primary_goal_any_of" in expected and generated.get("primary_goal") not in expected["primary_goal_any_of"]:
        return "bad_librarian_query"
    if metrics.get("sql_candidate_recall") == 0:
        return "sql_filter_removed_relevant_templates"
    if metrics.get("vector_hit_at_20") == 0:
        return "vector_similarity_failed"
    if metrics.get("vector_hit_at_20") == 1 and metrics.get("rerank_hit_at_3") == 0:
        return "reranking_failed"
    return "unknown"


def _enrich_with_relevance(rows: list[dict], expected: dict, rank_key: str = "rank") -> list[dict]:
    enriched = []
    for rank, row in enumerate(rows, start=1):
        item = {**row}
        item[rank_key] = item.get(rank_key, rank)
        grade = compute_relevance_grade(item, expected)
        item["relevance_grade"] = grade
        item["is_relevant"] = grade >= 2
        enriched.append(item)
    return enriched


def run_single_case(case: EvalCase, dry_run: bool = False) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "id": case.id,
        "user_query": case.user_query,
        "athlete_context": case.athlete_context,
        "expected": case.expected,
        "generated_librarian_query": None,
        "generated_semantic_labels": {},
        "sql_candidates": [],
        "vector_results_top20": [],
        "reranked_top3": [],
        "metrics": {},
        "errors": [],
    }

    athlete_ctx = build_full_athlete_context(case.athlete_context)
    target_duration_min = int(athlete_ctx.get("target_duration_min") or 90)
    state: dict[str, Any] = {
        "message": case.user_query,
        "athlete_context": athlete_ctx,
        "operator_plan": [],
    }

    try:
        from agents import library_agent as _library_agent
        from services.rag_service import rag_service as _rag_service

        generated_query = case.user_query if dry_run else _library_agent._generate_rag_query(state)
        generated_labels = _rag_service.parse_semantic_labels(generated_query)

        trace["generated_librarian_query"] = generated_query
        trace["generated_semantic_labels"] = generated_labels

        sql_candidates = []
        if not dry_run:
            sql_candidates = _rag_service._sql_filter(target_duration_min, athlete_ctx.get("tsb"), tolerance=0.4)
            if len(sql_candidates) < 5:
                sql_candidates = _rag_service._sql_filter(target_duration_min, athlete_ctx.get("tsb"), tolerance=0.6)
        sql_candidates = _enrich_with_relevance(sql_candidates, case.expected, rank_key="sql_rank")
        trace["sql_candidates"] = sql_candidates

        query_text = generated_query if dry_run else _rag_service.build_query_text(athlete_ctx, generated_query)
        trace.setdefault("debug", {})["query_text"] = query_text[:1000]

        vector_results = []
        if not dry_run:
            query_vector = _rag_service.generate_embedding(query_text)
            if query_vector is None:
                raise RuntimeError("Failed to generate query embedding")
            raw_vector_results = _rag_service._vector_search(sql_candidates, query_vector)
            candidates_by_id = {candidate["id"]: candidate for candidate in sql_candidates}
            vector_results = [{**candidates_by_id.get(row["id"], {}), **row} for row in raw_vector_results]

        vector_results = _enrich_with_relevance(vector_results, case.expected)
        trace["vector_results_top20"] = vector_results

        reranked = [] if dry_run else _rag_service.rerank_templates(
            templates=vector_results,
            generated_semantic_labels=generated_labels,
            athlete_context=athlete_ctx,
            top_k=3,
        )
        reranked = _enrich_with_relevance(reranked, case.expected)
        trace["reranked_top3"] = reranked

        vector_rels = [row.get("relevance_grade", 0) for row in vector_results]
        rerank_rels = [row.get("relevance_grade", 0) for row in reranked]

        label_scores = {
            "label_primary_goal_accuracy": label_check("primary_goal", generated_labels, case.expected),
            "label_work_zone_accuracy": label_check("work_zone", generated_labels, case.expected),
            "label_structure_type_accuracy": label_check("structure_type", generated_labels, case.expected),
            "label_fatigue_suitability_accuracy": label_check("fatigue_suitability", generated_labels, case.expected),
            "label_duration_class_accuracy": label_check("duration_class", generated_labels, case.expected),
        }

        trace["metrics"] = {
            "sql_candidate_count": len(sql_candidates),
            "sql_candidate_recall": 1 if any(row.get("is_relevant") for row in sql_candidates) else 0,
            "vector_hit_at_1": hit_at_k(vector_rels, 1),
            "vector_hit_at_3": hit_at_k(vector_rels, 3),
            "vector_hit_at_10": hit_at_k(vector_rels, 10),
            "vector_hit_at_20": hit_at_k(vector_rels, 20),
            "vector_precision_at_3": precision_at_k(vector_rels, 3),
            "vector_precision_at_10": precision_at_k(vector_rels, 10),
            "vector_mrr_at_20": mrr(vector_rels, 20),
            "vector_ndcg_at_3": ndcg(vector_rels, 3),
            "vector_ndcg_at_10": ndcg(vector_rels, 10),
            "rerank_hit_at_1": hit_at_k(rerank_rels, 1),
            "rerank_hit_at_3": hit_at_k(rerank_rels, 3),
            "rerank_precision_at_3": precision_at_k(rerank_rels, 3),
            "rerank_mrr_at_3": mrr(rerank_rels, 3),
            "rerank_ndcg_at_3": ndcg(rerank_rels, 3),
            **label_scores,
        }
        trace["failure_reason"] = infer_failure_reason(trace)
    except Exception as exc:
        LOG.exception("Error running case %s", case.id)
        trace["errors"].append(str(exc))
        trace["failure_reason"] = "runtime_error"

    return trace


def export_outputs(traces: list[dict], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    with open(outdir / "traces.json", "w", encoding="utf-8") as f:
        json.dump(traces, f, ensure_ascii=False, indent=2)

    with open(outdir / "per_query_metrics.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "user_query", "expected_primary_goal", "generated_primary_goal",
            "sql_candidate_count", "sql_candidate_recall",
            "vector_hit_at_1", "vector_hit_at_3", "vector_hit_at_10", "vector_hit_at_20",
            "vector_precision_at_3", "vector_precision_at_10", "vector_mrr_at_20",
            "vector_ndcg_at_3", "vector_ndcg_at_10",
            "rerank_hit_at_1", "rerank_hit_at_3", "rerank_precision_at_3",
            "rerank_mrr_at_3", "rerank_ndcg_at_3",
            "top1_title", "top1_primary_goal", "top1_relevance_grade", "failure_reason", "error",
        ])
        for trace in traces:
            metrics = trace.get("metrics", {})
            top1 = (trace.get("reranked_top3") or [{}])[0]
            writer.writerow([
                trace.get("id"),
                trace.get("user_query"),
                trace.get("expected", {}).get("primary_goal") or "|".join(trace.get("expected", {}).get("primary_goal_any_of", [])),
                trace.get("generated_semantic_labels", {}).get("primary_goal"),
                metrics.get("sql_candidate_count"),
                metrics.get("sql_candidate_recall"),
                metrics.get("vector_hit_at_1"),
                metrics.get("vector_hit_at_3"),
                metrics.get("vector_hit_at_10"),
                metrics.get("vector_hit_at_20"),
                metrics.get("vector_precision_at_3"),
                metrics.get("vector_precision_at_10"),
                metrics.get("vector_mrr_at_20"),
                metrics.get("vector_ndcg_at_3"),
                metrics.get("vector_ndcg_at_10"),
                metrics.get("rerank_hit_at_1"),
                metrics.get("rerank_hit_at_3"),
                metrics.get("rerank_precision_at_3"),
                metrics.get("rerank_mrr_at_3"),
                metrics.get("rerank_ndcg_at_3"),
                top1.get("title"),
                top1.get("primary_goal"),
                top1.get("relevance_grade"),
                trace.get("failure_reason"),
                "; ".join(trace.get("errors", [])),
            ])

    with open(outdir / "vector_results.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_id", "rank", "template_id", "title", "primary_goal", "secondary_goals",
            "work_zone", "structure_type", "fatigue_suitability", "load_level",
            "duration_class", "duration_min", "est_tss", "cosine_similarity",
            "relevance_grade", "is_relevant",
        ])
        for trace in traces:
            for row in trace.get("vector_results_top20", []):
                writer.writerow([
                    trace["id"], row.get("rank"), row.get("id"), row.get("title"),
                    row.get("primary_goal"), "|".join(row.get("secondary_goals") or []),
                    row.get("work_zone"), row.get("structure_type"), row.get("fatigue_suitability"),
                    row.get("load_level"), row.get("duration_class"), row.get("duration_min"),
                    row.get("est_tss"), row.get("cosine_similarity") or row.get("similarity"), row.get("relevance_grade"), row.get("is_relevant"),
                ])

    with open(outdir / "reranked_results.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_id", "rank", "template_id", "title", "primary_goal", "secondary_goals",
            "work_zone", "structure_type", "fatigue_suitability", "load_level",
            "duration_class", "duration_min", "est_tss", "cosine_similarity",
            "metadata_match_score", "context_fit_score", "duration_fit_score", "tss_fit_score",
            "hard_penalty", "combined_score", "relevance_grade", "is_relevant",
        ])
        for trace in traces:
            for row in trace.get("reranked_top3", []):
                writer.writerow([
                    trace["id"], row.get("rank"), row.get("id"), row.get("title"),
                    row.get("primary_goal"), "|".join(row.get("secondary_goals") or []),
                    row.get("work_zone"), row.get("structure_type"), row.get("fatigue_suitability"),
                    row.get("load_level"), row.get("duration_class"), row.get("duration_min"),
                    row.get("est_tss"), row.get("cosine_similarity"),
                    row.get("metadata_match_score"), row.get("context_fit_score"),
                    row.get("duration_fit_score"), row.get("tss_fit_score"),
                    row.get("hard_penalty"), row.get("combined_score"),
                    row.get("relevance_grade"), row.get("is_relevant"),
                ])

    with open(outdir / "sql_candidates.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_id", "template_id", "title", "primary_goal", "secondary_goals",
            "work_zone", "structure_type", "fatigue_suitability", "load_level",
            "duration_class", "duration_min", "est_tss", "relevance_grade", "is_relevant",
        ])
        for trace in traces:
            for row in trace.get("sql_candidates", []):
                writer.writerow([
                    trace["id"], row.get("id"), row.get("title"), row.get("primary_goal"),
                    "|".join(row.get("secondary_goals") or []), row.get("work_zone"),
                    row.get("structure_type"), row.get("fatigue_suitability"),
                    row.get("load_level"), row.get("duration_class"), row.get("duration_min"),
                    row.get("est_tss"), row.get("relevance_grade"), row.get("is_relevant"),
                ])

    with open(outdir / "generated_queries.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "user_query", "generated_librarian_query",
            "expected_primary_goal", "generated_primary_goal",
            "expected_work_zone", "generated_work_zone",
            "expected_structure_type", "generated_structure_type",
        ])
        for trace in traces:
            expected = trace.get("expected", {})
            writer.writerow([
                trace["id"], trace.get("user_query"), (trace.get("generated_librarian_query") or "").replace("\n", " ")[:600],
                expected.get("primary_goal") or "|".join(expected.get("primary_goal_any_of", [])),
                trace.get("generated_semantic_labels", {}).get("primary_goal"),
                expected.get("work_zone") or "|".join(expected.get("work_zone_any_of", [])),
                trace.get("generated_semantic_labels", {}).get("work_zone"),
                expected.get("structure_type") or "|".join(expected.get("structure_type_any_of", [])),
                trace.get("generated_semantic_labels", {}).get("structure_type"),
            ])

    with open(outdir / "errors.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["query_id", "failure_reason", "errors"])
        for trace in traces:
            if trace.get("errors"):
                writer.writerow([trace["id"], trace.get("failure_reason"), " | ".join(trace.get("errors", []))])


def aggregate_and_report(traces: list[dict], outdir: Path) -> None:
    aggregate: dict[str, Any] = {"num_queries": len(traces)}

    metric_keys = [
        "sql_candidate_recall",
        "vector_hit_at_1", "vector_hit_at_3", "vector_hit_at_10", "vector_hit_at_20",
        "vector_precision_at_3", "vector_precision_at_10", "vector_mrr_at_20",
        "vector_ndcg_at_3", "vector_ndcg_at_10",
        "rerank_hit_at_1", "rerank_hit_at_3", "rerank_precision_at_3",
        "rerank_mrr_at_3", "rerank_ndcg_at_3",
    ]
    for key in metric_keys:
        aggregate[f"{key}_mean"] = statistics.mean([trace.get("metrics", {}).get(key, 0) for trace in traces]) if traces else 0.0

    sql_counts = [trace.get("metrics", {}).get("sql_candidate_count", 0) for trace in traces]
    aggregate["sql_candidate_count_mean"] = statistics.mean(sql_counts) if sql_counts else 0.0
    aggregate["sql_candidate_count_median"] = statistics.median(sql_counts) if sql_counts else 0.0

    for key in [
        "label_primary_goal_accuracy",
        "label_work_zone_accuracy",
        "label_structure_type_accuracy",
        "label_fatigue_suitability_accuracy",
        "label_duration_class_accuracy",
    ]:
        aggregate[key] = _mean_skip_none([trace.get("metrics", {}).get(key) for trace in traces])

    by_goal: dict[str, list[dict]] = {}
    for trace in traces:
        expected = trace.get("expected", {})
        goal = expected.get("primary_goal")
        if not goal:
            goal_any = expected.get("primary_goal_any_of") or []
            goal = "|".join(goal_any) if goal_any else "unknown"
        by_goal.setdefault(goal, []).append(trace)

    by_goal_rows = []
    for goal, items in by_goal.items():
        by_goal_rows.append({
            "primary_goal": goal,
            "num_queries": len(items),
            "sql_candidate_recall": statistics.mean([it.get("metrics", {}).get("sql_candidate_recall", 0) for it in items]),
            "vector_hit_at_3": statistics.mean([it.get("metrics", {}).get("vector_hit_at_3", 0) for it in items]),
            "vector_ndcg_at_10": statistics.mean([it.get("metrics", {}).get("vector_ndcg_at_10", 0) for it in items]),
            "rerank_hit_at_3": statistics.mean([it.get("metrics", {}).get("rerank_hit_at_3", 0) for it in items]),
            "rerank_mrr_at_3": statistics.mean([it.get("metrics", {}).get("rerank_mrr_at_3", 0) for it in items]),
            "rerank_ndcg_at_3": statistics.mean([it.get("metrics", {}).get("rerank_ndcg_at_3", 0) for it in items]),
            "rerank_precision_at_3": statistics.mean([it.get("metrics", {}).get("rerank_precision_at_3", 0) for it in items]),
        })

    with open(outdir / "aggregate_metrics.json", "w", encoding="utf-8") as f:
        json.dump({"aggregate": aggregate, "by_primary_goal": by_goal_rows}, f, indent=2, ensure_ascii=False)

    with open(outdir / "metrics_by_primary_goal.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "primary_goal", "num_queries", "sql_candidate_recall", "vector_hit_at_3",
            "vector_ndcg_at_10", "rerank_hit_at_3", "rerank_mrr_at_3",
            "rerank_ndcg_at_3", "rerank_precision_at_3",
        ])
        for row in by_goal_rows:
            writer.writerow([
                row["primary_goal"], row["num_queries"], row["sql_candidate_recall"],
                row["vector_hit_at_3"], row["vector_ndcg_at_10"], row["rerank_hit_at_3"],
                row["rerank_mrr_at_3"], row["rerank_ndcg_at_3"], row["rerank_precision_at_3"],
            ])

    failures = [trace for trace in traces if trace.get("failure_reason") != "unknown" or trace.get("metrics", {}).get("rerank_hit_at_3", 0) == 0]
    lines = [
        "# Librarian RAG Evaluation",
        "",
        f"Fecha: {datetime.now(UTC).isoformat()}",
        f"Número de queries: {aggregate['num_queries']}",
        "",
        "## Nota metodológica",
        "- Evaluación local de integración del pipeline Librarian/RAG.",
        "- No evalúa el Workout Editor.",
        "- No compara variantes alternativas del sistema.",
        "- Evalúa 3 fases: SQL filtering, vector search y metadata-aware reranking final.",
        "",
        "El metadata-aware reranker no utiliza las etiquetas esperadas del dataset de evaluación. Utiliza únicamente las labels generadas por el Librarian, los metadatos disponibles en workout_library y el contexto del atleta. Los campos expected y relevant_title_prefixes se reservan exclusivamente para calcular métricas.",
        "",
        "## Métricas globales por fase",
    ]
    for key, value in aggregate.items():
        lines.append(f"- **{key}**: {value}")

    lines.append("")
    lines.append("## Métricas por primary_goal")
    for row in by_goal_rows:
        lines.append(
            f"- **{row['primary_goal']}**: n={row['num_queries']}, sql_recall={row['sql_candidate_recall']}, "
            f"vector_hit@3={row['vector_hit_at_3']}, rerank_hit@3={row['rerank_hit_at_3']}, "
            f"rerank_ndcg@3={row['rerank_ndcg_at_3']}"
        )

    lines.append("")
    lines.append("## Queries fallidas")
    for trace in failures[:10]:
        lines.append(f"- **{trace['id']}**: {trace['user_query']}")
        lines.append(f"  expected: {json.dumps(trace.get('expected'), ensure_ascii=False)}")
        lines.append(f"  generated_librarian_query: {trace.get('generated_librarian_query')}")
        lines.append(f"  top3 final: {[row.get('title') for row in trace.get('reranked_top3', [])]}")
        lines.append(f"  relevance_grades: {[row.get('relevance_grade') for row in trace.get('reranked_top3', [])]}")
        lines.append(f"  failure_reason: {trace.get('failure_reason')}")

    lines.append("")
    lines.append("## Interpretación breve")
    lines.append("- Las métricas de SQL indican si la plantilla relevante sobrevive al filtrado inicial.")
    lines.append("- Las métricas vectoriales miden recuperación semántica intermedia antes del reranker.")
    lines.append("- Las métricas finales del reranker representan el comportamiento real del sistema.")

    with open(outdir / "aggregate_metrics.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_plots(traces: list[dict], outdir: Path) -> None:
    if plt is None or np is None:
        LOG.warning("matplotlib or numpy not available; skipping plots")
        return

    outdir.mkdir(parents=True, exist_ok=True)
    phase_labels = ["SQL Recall", "Vector Hit@3", "Vector nDCG@10", "Rerank Hit@3", "Rerank nDCG@3"]
    phase_values = [
        statistics.mean([trace.get("metrics", {}).get("sql_candidate_recall", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("vector_hit_at_3", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("vector_ndcg_at_10", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("rerank_hit_at_3", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("rerank_ndcg_at_3", 0) for trace in traces]) if traces else 0.0,
    ]
    x = np.arange(len(phase_labels))

    plt.figure(figsize=(10, 5))
    plt.bar(x, phase_values, color=["#4C78A8", "#72B7B2", "#54A24B", "#E45756", "#F58518"])
    plt.xticks(x, phase_labels, rotation=20, ha="right")
    plt.ylim(0, 1)
    plt.title("Phase Metrics")
    plt.tight_layout()
    plt.savefig(outdir / "phase_metrics_bar.png")
    plt.close()

    plt.figure(figsize=(8, 4))
    hit_values = [
        statistics.mean([trace.get("metrics", {}).get("sql_candidate_recall", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("vector_hit_at_3", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("rerank_hit_at_3", 0) for trace in traces]) if traces else 0.0,
    ]
    plt.bar(["SQL", "Vector", "Rerank"], hit_values, color=["#4C78A8", "#72B7B2", "#E45756"])
    plt.ylim(0, 1)
    plt.title("Hit@3 by Phase")
    plt.tight_layout()
    plt.savefig(outdir / "hit_at_3_by_phase.png")
    plt.close()

    plt.figure(figsize=(8, 4))
    ndcg_values = [
        statistics.mean([trace.get("metrics", {}).get("vector_ndcg_at_3", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("vector_ndcg_at_10", 0) for trace in traces]) if traces else 0.0,
        statistics.mean([trace.get("metrics", {}).get("rerank_ndcg_at_3", 0) for trace in traces]) if traces else 0.0,
    ]
    plt.bar(["Vector nDCG@3", "Vector nDCG@10", "Rerank nDCG@3"], ndcg_values, color=["#72B7B2", "#54A24B", "#E45756"])
    plt.ylim(0, 1)
    plt.title("nDCG by Phase")
    plt.tight_layout()
    plt.savefig(outdir / "ndcg_by_phase.png")
    plt.close()

    by_goal: dict[str, list[dict]] = {}
    for trace in traces:
        goal = trace.get("expected", {}).get("primary_goal") or "|".join(trace.get("expected", {}).get("primary_goal_any_of", [])) or "unknown"
        by_goal.setdefault(goal, []).append(trace)
    goals = list(by_goal.keys())
    rerank_hit3 = [statistics.mean([trace.get("metrics", {}).get("rerank_hit_at_3", 0) for trace in by_goal[goal]]) for goal in goals]
    plt.figure(figsize=(12, 5))
    plt.bar(goals, rerank_hit3, color="#E45756")
    plt.ylim(0, 1)
    plt.title("Rerank Hit@3 by Primary Goal")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(outdir / "metrics_by_primary_goal.png")
    plt.close()

    sql_counts = [trace.get("metrics", {}).get("sql_candidate_count", 0) for trace in traces]
    plt.figure(figsize=(8, 4))
    plt.hist(sql_counts, bins=min(20, max(5, len(set(sql_counts)) or 5)))
    plt.title("SQL Candidate Count Distribution")
    plt.tight_layout()
    plt.savefig(outdir / "sql_candidate_count_distribution.png")
    plt.close()

    top1_grades = [((trace.get("reranked_top3") or [{}])[0]).get("relevance_grade", 0) for trace in traces]
    plt.figure(figsize=(6, 4))
    plt.hist(top1_grades, bins=[-0.5, 0.5, 1.5, 2.5, 3.5], align="mid", rwidth=0.7)
    plt.xticks([0, 1, 2, 3])
    plt.title("Top1 Relevance Distribution")
    plt.tight_layout()
    plt.savefig(outdir / "top1_relevance_distribution.png")
    plt.close()

    heat = np.zeros((3, 4), dtype=int)
    for trace in traces:
        reranked = trace.get("reranked_top3", [])
        for pos in range(3):
            grade = reranked[pos].get("relevance_grade", 0) if pos < len(reranked) else 0
            heat[pos, grade] += 1
    np.savetxt(outdir / "rerank_position_relevance_heatmap.csv", heat, fmt="%d", delimiter=",")
    plt.figure(figsize=(6, 4))
    plt.imshow(heat, cmap="Blues", aspect="auto")
    plt.colorbar()
    plt.yticks([0, 1, 2], ["pos1", "pos2", "pos3"])
    plt.xticks([0, 1, 2, 3], ["g0", "g1", "g2", "g3"])
    plt.title("Rerank Position vs Relevance")
    plt.tight_layout()
    plt.savefig(outdir / "rerank_position_relevance_heatmap.png")
    plt.close()

    failure_reasons = {}
    for trace in traces:
        failure_reasons[trace.get("failure_reason", "unknown")] = failure_reasons.get(trace.get("failure_reason", "unknown"), 0) + 1
    plt.figure(figsize=(8, 4))
    plt.bar(list(failure_reasons.keys()), list(failure_reasons.values()), color="#B279A2")
    plt.title("Failure Reason Distribution")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(outdir / "failure_reason_distribution.png")
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="evaluation_outputs/librarian_rag")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--queries-file", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--only-query-id", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        LOG.setLevel(logging.DEBUG)

    cases = load_eval_cases(args.queries_file)
    if args.only_query_id:
        cases = [case for case in cases if case.id == args.only_query_id]
    cases = cases[:args.limit]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.output_dir) / ts
    outdir.mkdir(parents=True, exist_ok=True)

    traces = []
    for case in cases:
        LOG.info("Running case %s", case.id)
        traces.append(run_single_case(case, dry_run=args.dry_run))

    export_outputs(traces, outdir)
    aggregate_and_report(traces, outdir)
    if not args.no_plots:
        generate_plots(traces, outdir / "plots")

    print("Evaluation finished.")
    print("")
    print("Output directory:")
    print(outdir)


if __name__ == "__main__":
    main()
