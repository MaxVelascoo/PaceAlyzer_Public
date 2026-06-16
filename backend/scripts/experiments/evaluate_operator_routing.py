"""Evaluación del routing del Operator (Experimento B).

Evalúa únicamente el nodo Operator:
state fixture -> operator_agent.run -> operator_plan

No ejecuta el resto de agentes del sistema.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import statistics
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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

LOG = logging.getLogger("evaluate_operator_routing")
logging.basicConfig(level=logging.INFO)

AGENT_NAMES = [
    "librarian",
    "workout_editor",
    "nutrition_editor",
    "week_planner",
    "explainer",
]
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
WELLNESS_MIN_DAYS = 14


@dataclass
class EvalCase:
    id: str
    group: str
    category: str
    date: str
    user_query: str
    athlete_context: dict
    expected_agents: list[str]
    current_workout: dict | None = None
    conversation_history: list[dict] | None = None
    notes: str | None = None


def load_eval_cases(path: str | None = None) -> list[EvalCase]:
    if path and yaml:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [EvalCase(**item) for item in data]

    repo_yaml = _script_path.parents[3] / "evaluation" / "operator_routing_eval_queries.yaml"
    if not repo_yaml.exists():
        repo_yaml = _script_path.parents[1] / "evaluation" / "operator_routing_eval_queries.yaml"
    if not repo_yaml.exists():
        repo_yaml = Path.cwd() / "evaluation" / "operator_routing_eval_queries.yaml"

    if repo_yaml.exists() and yaml:
        with open(repo_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [EvalCase(**item) for item in data]

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


def build_full_athlete_context(minimal_context: dict, reference_date: str) -> dict:
    ref_day = date.fromisoformat(reference_date)
    monday = ref_day - timedelta(days=ref_day.weekday())
    full_ctx = {**(minimal_context or {})}
    defaults = {
        "ftp": 275,
        "weight": 75.0,
        "w_per_kg": 3.67,
        "age": 35,
        "max_hr": 185,
        "goal": full_ctx.get("objective") or "improve_endurance",
        "available_days": 5,
        "next_event_name": None,
        "next_event_date": None,
        "next_event_days": None,
        "ctl": 55.0,
        "atl": 30.0,
        "km_avg_4w": 200.0,
        "hours_avg_4w": 12.0,
        "tss_avg_4w": 800.0,
        "last_training_date": (ref_day - timedelta(days=1)).isoformat(),
        "last_training_name": "Easy ride",
        "last_training_tss": 120.0,
        "last_training_type": "endurance",
        "done_this_week": 3,
        "tss_week": 600,
        "planned_this_week": [
            {
                "date": monday.isoformat(),
                "title": "Rodaje base",
                "duration_min": 60,
                "estimated_tss": 45,
            }
        ],
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


def format_context_for_prompt_local(ctx: dict) -> str:
    lines = ["── Contexto del atleta ──────────────────────────────"]

    ftp_str = f"{ctx['ftp']} W" if ctx.get("ftp") else "no definido"
    weight_str = f"{ctx['weight']} kg" if ctx.get("weight") else "no definido"
    wkg_str = f"{ctx['w_per_kg']} W/kg" if ctx.get("w_per_kg") else "—"
    age_str = f"{ctx['age']} años" if ctx.get("age") else "—"
    hr_str = f"{ctx['max_hr']} ppm" if ctx.get("max_hr") else "—"
    goal_str = ctx.get("goal") or "no especificado"
    days_str = str(ctx.get("available_days")) if ctx.get("available_days") else "5"

    lines.append(f"FTP: {ftp_str} | Peso: {weight_str} | W/kg: {wkg_str}")
    lines.append(f"FC máxima: {hr_str} | Edad: {age_str}")
    lines.append(f"Objetivo: {goal_str} | Días disponibles: {days_str}/semana")

    if ctx.get("next_event_name"):
        lines.append(f"Próximo evento: {ctx['next_event_name']} ({ctx['next_event_date']}, en {ctx['next_event_days']} días)")
    else:
        lines.append("Próximo evento: ninguno registrado")

    lines.append("")
    ctl_str = f"{ctx['ctl']:.1f}" if ctx.get("ctl") is not None else "—"
    atl_str = f"{ctx['atl']:.1f}" if ctx.get("atl") is not None else "—"
    tsb_str = f"{ctx['tsb']:+.1f}" if ctx.get("tsb") is not None else "—"
    lines.append(f"CTL (fitness): {ctl_str} | ATL (fatiga): {atl_str} | TSB (balance): {tsb_str}")

    if ctx.get("km_avg_4w") is not None:
        lines.append(
            f"Promedio últimas 4 semanas: {ctx['km_avg_4w']} km/sem, "
            f"{ctx['hours_avg_4w']} h/sem, {int(ctx['tss_avg_4w'])} TSS/sem"
        )

    if ctx.get("last_training_date"):
        last_tss = ctx.get("last_training_tss")
        last_type = ctx.get("last_training_type", "")
        tss_piece = f" | TSS: {int(last_tss)}" if last_tss else ""
        race_piece = " [CARRERA/COMPETICIÓN]" if last_type and "race" in str(last_type).lower() else ""
        lines.append(f"Último entreno: {ctx['last_training_date']} — {ctx['last_training_name'] or 'sin nombre'}{tss_piece}{race_piece}")

    lines.append("")
    lines.append(f"Esta semana: {ctx['done_this_week']} entrenos realizados | TSS acumulado: {int(ctx['tss_week'])}")

    if ctx.get("planned_this_week"):
        planned_str = ", ".join(
            f"{p['date']} {p['title']} ({p['duration_min']}min"
            + (f", ~{int(p['estimated_tss'])} TSS" if p.get("estimated_tss") else "")
            + ")"
            for p in ctx["planned_this_week"]
        )
        lines.append(f"Planificado esta semana: {planned_str}")

    if ctx.get("blocked_this_week"):
        blocked_str = ", ".join(
            f"{b['date']}" + (f" ({b['reason']})" if b.get("reason") else "")
            for b in ctx["blocked_this_week"]
        )
        lines.append(f"Días bloqueados esta semana: {blocked_str}")

    wellness_days = ctx.get("wellness_days_available", 0)
    has_hrv = ctx.get("hrv_signal") is not None
    has_hr = ctx.get("resting_hr_signal") is not None
    if has_hrv or has_hr:
        lines.append("")
        lines.append("Señales de bienestar de hoy (basadas en línea base personal):")
        if has_hrv:
            signal_map = {
                "positive": "↑ positiva (bien recuperado)",
                "neutral": "→ normal",
                "negative": "↓ negativa (fatiga/estrés)",
            }
            dev = ctx["hrv_deviation_pct"]
            sign = "+" if dev >= 0 else ""
            lines.append(f"  HRV: {sign}{dev}% sobre línea base ({ctx['hrv_baseline']} ms) → señal {signal_map[ctx['hrv_signal']]}")
        if has_hr:
            signal_map = {
                "positive": "↓ positiva (bien recuperado)",
                "neutral": "→ normal",
                "negative": "↑ negativa (fatiga/estrés)",
            }
            dev = ctx["resting_hr_deviation_pct"]
            sign = "+" if dev >= 0 else ""
            lines.append(f"  FC reposo: {sign}{dev}% sobre línea base ({ctx['resting_hr_baseline']} bpm) → señal {signal_map[ctx['resting_hr_signal']]}")
    elif wellness_days > 0:
        lines.append(f"  (Señales HRV/FC reposo no disponibles aún: {wellness_days}/{WELLNESS_MIN_DAYS} días registrados)")

    lines.append("─────────────────────────────────────────────────────")
    return "\n".join(lines)


@contextmanager
def patch_operator_today(operator_module: Any, fixed_day: date):
    real_date_class = operator_module.date

    class FixedDate(real_date_class):
        @classmethod
        def today(cls):
            return fixed_day

    operator_module.date = FixedDate
    try:
        yield
    finally:
        operator_module.date = real_date_class


def render_operator_user_prompt(operator_module: Any, state: dict[str, Any]) -> str:
    workout_summary = "No hay entreno planificado para ese día."
    if state.get("current_workout"):
        workout = state["current_workout"]
        workout_summary = f"Entreno actual: '{workout.get('title', 'Sin título')}', status: {workout.get('status', '?')}"

    history = state.get("conversation_history", [])
    history_text = ""
    if history:
        lines = [f"{msg['role'].upper()}: {msg['content']}" for msg in history]
        history_text = "\nHistorial reciente:\n" + "\n".join(lines) + "\n"

    return f"""{operator_module._week_context()}
{history_text}
{format_context_for_prompt_local(state["athlete_context"]) if state.get("athlete_context") else ""}

Contexto del día {state['date']}:
{workout_summary}

Mensaje actual del usuario: "{state['message']}" """


def is_iso_date_present(text: str | None) -> bool:
    return bool(text and ISO_DATE_RE.search(text))


def infer_failure_reason(trace: dict[str, Any]) -> str:
    metrics = trace.get("metrics", {})
    if trace.get("errors"):
        return "runtime_error"
    if metrics.get("predicted_plan_length", 0) == 0:
        return "empty_plan"
    if metrics.get("exact_plan_match") == 1:
        if metrics.get("all_instructions_have_iso_date") == 0:
            return "invalid_instruction_date"
        return "none"
    if metrics.get("exact_set_match") == 1 and metrics.get("order_match") == 0:
        return "wrong_order"
    if metrics.get("missing_agents_count", 0) > 0 and metrics.get("extra_agents_count", 0) == 0:
        return "missing_agents"
    if metrics.get("extra_agents_count", 0) > 0 and metrics.get("missing_agents_count", 0) == 0:
        return "spurious_agents"
    if metrics.get("missing_agents_count", 0) > 0 and metrics.get("extra_agents_count", 0) > 0:
        return "mixed_routing_error"
    if metrics.get("all_instructions_have_iso_date") == 0:
        return "invalid_instruction_date"
    if metrics.get("librarian_order_ok") == 0:
        return "invalid_librarian_order"
    return "unknown"


def run_single_case(case: EvalCase) -> dict[str, Any]:
    from agents import operator_agent

    athlete_context = build_full_athlete_context(case.athlete_context or {}, case.date)
    state = {
        "date": case.date,
        "message": case.user_query,
        "athlete_context": athlete_context,
        "current_workout": case.current_workout,
        "conversation_history": case.conversation_history or [],
    }

    trace: dict[str, Any] = {
        "id": case.id,
        "group": case.group,
        "category": case.category,
        "date": case.date,
        "user_query": case.user_query,
        "notes": case.notes,
        "athlete_context": case.athlete_context,
        "current_workout": case.current_workout,
        "conversation_history": case.conversation_history or [],
        "expected_agents": case.expected_agents,
        "predicted_plan": [],
        "operator_system_prompt": operator_agent.SYSTEM_PROMPT,
        "operator_user_prompt": None,
        "metrics": {},
        "errors": [],
    }

    try:
        fixed_day = date.fromisoformat(case.date)
        with patch_operator_today(operator_agent, fixed_day):
            trace["operator_user_prompt"] = render_operator_user_prompt(operator_agent, state)
            result_state = operator_agent.run(state)

        predicted_plan = result_state.get("operator_plan", []) or []
        predicted_agents = [step.get("agent") for step in predicted_plan if step.get("agent")]
        expected_agents = case.expected_agents

        predicted_set = set(predicted_agents)
        expected_set = set(expected_agents)
        missing_agents = [agent for agent in expected_agents if agent not in predicted_set]
        extra_agents = [agent for agent in predicted_agents if agent not in expected_set]

        steps_with_dates = [
            step for step in predicted_plan
            if is_iso_date_present(step.get("instruction"))
        ]
        all_instructions_have_iso_date = int(
            len(predicted_plan) > 0 and len(steps_with_dates) == len(predicted_plan)
        )

        librarian_order_ok = 1
        if "librarian" in predicted_agents and "workout_editor" in predicted_agents:
            librarian_order_ok = int(predicted_agents.index("librarian") < predicted_agents.index("workout_editor"))
        elif "librarian" in predicted_agents and "week_planner" in predicted_agents:
            librarian_order_ok = int(predicted_agents.index("librarian") < predicted_agents.index("week_planner"))

        metrics = {
            "expected_plan_length": len(expected_agents),
            "predicted_plan_length": len(predicted_agents),
            "exact_plan_match": int(predicted_agents == expected_agents),
            "exact_set_match": int(predicted_set == expected_set),
            "order_match": int(predicted_agents == expected_agents),
            "first_agent_match": int(
                bool(predicted_agents) and bool(expected_agents) and predicted_agents[0] == expected_agents[0]
            ),
            "non_empty_plan": int(len(predicted_agents) > 0),
            "all_expected_present": int(all(agent in predicted_set for agent in expected_agents)),
            "no_unexpected_agents": int(len(extra_agents) == 0),
            "missing_agents_count": len(missing_agents),
            "extra_agents_count": len(extra_agents),
            "all_instructions_have_iso_date": all_instructions_have_iso_date,
            "instruction_date_coverage": (
                len(steps_with_dates) / len(predicted_plan) if predicted_plan else 0.0
            ),
            "librarian_order_ok": librarian_order_ok,
        }

        for agent in AGENT_NAMES:
            metrics[f"expected_{agent}"] = int(agent in expected_set)
            metrics[f"predicted_{agent}"] = int(agent in predicted_set)

        trace["predicted_plan"] = predicted_plan
        trace["metrics"] = metrics
        trace["missing_agents"] = missing_agents
        trace["extra_agents"] = extra_agents
        trace["predicted_agents"] = predicted_agents
        trace["failure_reason"] = infer_failure_reason(trace)
    except Exception as exc:
        LOG.exception("Error running case %s", case.id)
        trace["errors"].append(str(exc))
        trace["predicted_agents"] = []
        trace["missing_agents"] = list(case.expected_agents)
        trace["extra_agents"] = []
        trace["failure_reason"] = "runtime_error"

    return trace


def _mean(values: list[int | float]) -> float:
    return statistics.mean(values) if values else 0.0


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def export_outputs(traces: list[dict[str, Any]], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    with open(outdir / "traces.json", "w", encoding="utf-8") as f:
        json.dump(traces, f, ensure_ascii=False, indent=2)

    with open(outdir / "per_query_metrics.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "group", "category", "date", "user_query",
            "expected_agents", "predicted_agents",
            "exact_plan_match", "exact_set_match", "first_agent_match",
            "non_empty_plan", "all_expected_present", "no_unexpected_agents",
            "missing_agents_count", "extra_agents_count",
            "all_instructions_have_iso_date", "instruction_date_coverage",
            "librarian_order_ok", "failure_reason", "error",
        ])
        for trace in traces:
            metrics = trace.get("metrics", {})
            writer.writerow([
                trace.get("id"),
                trace.get("group"),
                trace.get("category"),
                trace.get("date"),
                trace.get("user_query"),
                " | ".join(trace.get("expected_agents", [])),
                " | ".join(trace.get("predicted_agents", [])),
                metrics.get("exact_plan_match"),
                metrics.get("exact_set_match"),
                metrics.get("first_agent_match"),
                metrics.get("non_empty_plan"),
                metrics.get("all_expected_present"),
                metrics.get("no_unexpected_agents"),
                metrics.get("missing_agents_count"),
                metrics.get("extra_agents_count"),
                metrics.get("all_instructions_have_iso_date"),
                metrics.get("instruction_date_coverage"),
                metrics.get("librarian_order_ok"),
                trace.get("failure_reason"),
                "; ".join(trace.get("errors", [])),
            ])

    with open(outdir / "predicted_plans.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_id", "step_index", "agent", "instruction", "has_iso_date",
        ])
        for trace in traces:
            for idx, step in enumerate(trace.get("predicted_plan", []), start=1):
                writer.writerow([
                    trace.get("id"),
                    idx,
                    step.get("agent"),
                    step.get("instruction"),
                    int(is_iso_date_present(step.get("instruction"))),
                ])

    with open(outdir / "errors.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["query_id", "failure_reason", "errors"])
        for trace in traces:
            if trace.get("errors"):
                writer.writerow([
                    trace.get("id"),
                    trace.get("failure_reason"),
                    " | ".join(trace.get("errors", [])),
                ])


def aggregate_and_report(traces: list[dict[str, Any]], outdir: Path) -> None:
    aggregate: dict[str, Any] = {
        "num_queries": len(traces),
        "exact_plan_accuracy": _mean([t.get("metrics", {}).get("exact_plan_match", 0) for t in traces]),
        "exact_set_accuracy": _mean([t.get("metrics", {}).get("exact_set_match", 0) for t in traces]),
        "first_agent_accuracy": _mean([t.get("metrics", {}).get("first_agent_match", 0) for t in traces]),
        "non_empty_plan_rate": _mean([t.get("metrics", {}).get("non_empty_plan", 0) for t in traces]),
        "all_expected_present_rate": _mean([t.get("metrics", {}).get("all_expected_present", 0) for t in traces]),
        "no_unexpected_agents_rate": _mean([t.get("metrics", {}).get("no_unexpected_agents", 0) for t in traces]),
        "instruction_iso_date_plan_rate": _mean([t.get("metrics", {}).get("all_instructions_have_iso_date", 0) for t in traces]),
        "instruction_iso_date_step_coverage": _mean([t.get("metrics", {}).get("instruction_date_coverage", 0.0) for t in traces]),
        "librarian_order_accuracy": _mean([t.get("metrics", {}).get("librarian_order_ok", 1) for t in traces]),
        "avg_missing_agents": _mean([t.get("metrics", {}).get("missing_agents_count", 0) for t in traces]),
        "avg_extra_agents": _mean([t.get("metrics", {}).get("extra_agents_count", 0) for t in traces]),
        "avg_expected_plan_length": _mean([t.get("metrics", {}).get("expected_plan_length", 0) for t in traces]),
        "avg_predicted_plan_length": _mean([t.get("metrics", {}).get("predicted_plan_length", 0) for t in traces]),
    }

    by_group: dict[str, list[dict[str, Any]]] = {}
    by_category: dict[str, list[dict[str, Any]]] = {}
    failure_counts: dict[str, int] = {}
    for trace in traces:
        by_group.setdefault(trace.get("group", "unknown"), []).append(trace)
        by_category.setdefault(trace.get("category", "unknown"), []).append(trace)
        failure = trace.get("failure_reason", "unknown")
        failure_counts[failure] = failure_counts.get(failure, 0) + 1

    agent_rows = []
    for agent in AGENT_NAMES:
        tp = fp = fn = tn = 0
        for trace in traces:
            metrics = trace.get("metrics", {})
            expected = metrics.get(f"expected_{agent}", 0)
            predicted = metrics.get(f"predicted_{agent}", 0)
            if expected and predicted:
                tp += 1
            elif not expected and predicted:
                fp += 1
            elif expected and not predicted:
                fn += 1
            else:
                tn += 1
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        agent_rows.append({
            "agent": agent,
            "support": tp + fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        })

    group_rows = []
    for group, items in by_group.items():
        group_rows.append({
            "group": group,
            "num_queries": len(items),
            "exact_plan_accuracy": _mean([t.get("metrics", {}).get("exact_plan_match", 0) for t in items]),
            "exact_set_accuracy": _mean([t.get("metrics", {}).get("exact_set_match", 0) for t in items]),
            "first_agent_accuracy": _mean([t.get("metrics", {}).get("first_agent_match", 0) for t in items]),
            "instruction_iso_date_rate": _mean([t.get("metrics", {}).get("all_instructions_have_iso_date", 0) for t in items]),
        })

    category_rows = []
    for category, items in by_category.items():
        category_rows.append({
            "category": category,
            "num_queries": len(items),
            "exact_plan_accuracy": _mean([t.get("metrics", {}).get("exact_plan_match", 0) for t in items]),
            "exact_set_accuracy": _mean([t.get("metrics", {}).get("exact_set_match", 0) for t in items]),
            "first_agent_accuracy": _mean([t.get("metrics", {}).get("first_agent_match", 0) for t in items]),
            "avg_missing_agents": _mean([t.get("metrics", {}).get("missing_agents_count", 0) for t in items]),
            "avg_extra_agents": _mean([t.get("metrics", {}).get("extra_agents_count", 0) for t in items]),
        })

    with open(outdir / "aggregate_metrics.json", "w", encoding="utf-8") as f:
        json.dump({
            "aggregate": aggregate,
            "by_group": group_rows,
            "by_category": category_rows,
            "by_agent": agent_rows,
            "failure_reasons": failure_counts,
        }, f, indent=2, ensure_ascii=False)

    with open(outdir / "metrics_by_group.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "num_queries", "exact_plan_accuracy", "exact_set_accuracy", "first_agent_accuracy", "instruction_iso_date_rate"])
        for row in group_rows:
            writer.writerow([
                row["group"], row["num_queries"], row["exact_plan_accuracy"],
                row["exact_set_accuracy"], row["first_agent_accuracy"], row["instruction_iso_date_rate"],
            ])

    with open(outdir / "metrics_by_category.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "num_queries", "exact_plan_accuracy", "exact_set_accuracy", "first_agent_accuracy", "avg_missing_agents", "avg_extra_agents"])
        for row in category_rows:
            writer.writerow([
                row["category"], row["num_queries"], row["exact_plan_accuracy"],
                row["exact_set_accuracy"], row["first_agent_accuracy"],
                row["avg_missing_agents"], row["avg_extra_agents"],
            ])

    with open(outdir / "agent_metrics.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent", "support", "precision", "recall", "f1", "tp", "fp", "fn", "tn"])
        for row in agent_rows:
            writer.writerow([
                row["agent"], row["support"], row["precision"], row["recall"], row["f1"],
                row["tp"], row["fp"], row["fn"], row["tn"],
            ])

    failed_cases = [trace for trace in traces if trace.get("failure_reason") not in {"none"}]
    lines = [
        "# Operator Routing Evaluation",
        "",
        f"Fecha: {datetime.now(timezone.utc).isoformat()}",
        f"Número de queries: {aggregate['num_queries']}",
        "",
        "## Nota metodológica",
        "- Evaluación local de integración del nodo `Operator`.",
        "- No ejecuta `librarian`, `workout_editor`, `nutrition_editor`, `week_planner` ni `explainer`.",
        "- Ejecuta el `system prompt` real y reconstruye el `user prompt` con el mismo contexto que producción.",
        "- Evalúa calidad de routing, orden del plan e higiene mínima de las instrucciones generadas.",
        "",
        "## Métricas globales",
    ]
    for key, value in aggregate.items():
        lines.append(f"- **{key}**: {value}")

    lines.extend(["", "## Métricas por Grupo"])
    for row in group_rows:
        lines.append(
            f"- **{row['group']}**: n={row['num_queries']}, "
            f"exact_plan={row['exact_plan_accuracy']}, exact_set={row['exact_set_accuracy']}, "
            f"first_agent={row['first_agent_accuracy']}"
        )

    lines.extend(["", "## Métricas por Categoría"])
    for row in category_rows:
        lines.append(
            f"- **{row['category']}**: n={row['num_queries']}, "
            f"exact_plan={row['exact_plan_accuracy']}, exact_set={row['exact_set_accuracy']}, "
            f"avg_missing={row['avg_missing_agents']}, avg_extra={row['avg_extra_agents']}"
        )

    lines.extend(["", "## Métricas por Agente"])
    for row in agent_rows:
        lines.append(
            f"- **{row['agent']}**: support={row['support']}, precision={row['precision']}, "
            f"recall={row['recall']}, f1={row['f1']}"
        )

    lines.extend(["", "## Distribución de Fallos"])
    for reason, count in sorted(failure_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- **{reason}**: {count}")

    lines.extend(["", "## Queries Fallidas"])
    for trace in failed_cases[:15]:
        lines.append(f"- **{trace['id']}**: {trace['user_query']}")
        lines.append(f"  - expected_agents: {trace.get('expected_agents')}")
        lines.append(f"  - predicted_agents: {trace.get('predicted_agents')}")
        lines.append(f"  - failure_reason: {trace.get('failure_reason')}")
        lines.append(f"  - predicted_plan: {trace.get('predicted_plan')}")

    lines.extend([
        "",
        "## Interpretación breve",
        "- `exact_plan_accuracy` mide acierto completo del plan y del orden esperado.",
        "- `exact_set_accuracy` separa errores de routing puro de errores de orden.",
        "- Las métricas por agente ayudan a detectar si el Operator tiende a omitir o sobreactivar agentes concretos.",
        "- `instruction_iso_date_plan_rate` no valida semántica completa de fechas, pero sí que el Operator está generando instrucciones con formato utilizable por el resto del sistema.",
    ])

    with open(outdir / "aggregate_metrics.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_plots(traces: list[dict[str, Any]], outdir: Path) -> None:
    if plt is None or np is None:
        LOG.warning("matplotlib or numpy not available; skipping plots")
        return

    outdir.mkdir(parents=True, exist_ok=True)

    overall_labels = [
        "Exact Plan",
        "Exact Set",
        "First Agent",
        "All Expected",
        "No Unexpected",
        "ISO Dates",
    ]
    overall_values = [
        _mean([t.get("metrics", {}).get("exact_plan_match", 0) for t in traces]),
        _mean([t.get("metrics", {}).get("exact_set_match", 0) for t in traces]),
        _mean([t.get("metrics", {}).get("first_agent_match", 0) for t in traces]),
        _mean([t.get("metrics", {}).get("all_expected_present", 0) for t in traces]),
        _mean([t.get("metrics", {}).get("no_unexpected_agents", 0) for t in traces]),
        _mean([t.get("metrics", {}).get("all_instructions_have_iso_date", 0) for t in traces]),
    ]
    x = np.arange(len(overall_labels))
    plt.figure(figsize=(10, 5))
    plt.bar(x, overall_values, color=["#4C78A8", "#72B7B2", "#54A24B", "#E45756", "#F58518", "#B279A2"])
    plt.xticks(x, overall_labels, rotation=20, ha="right")
    plt.ylim(0, 1)
    plt.title("Operator Routing Overall Metrics")
    plt.tight_layout()
    plt.savefig(outdir / "overall_metrics_bar.png")
    plt.close()

    groups = sorted({t.get("group", "unknown") for t in traces})
    group_acc = [
        _mean([t.get("metrics", {}).get("exact_plan_match", 0) for t in traces if t.get("group") == group])
        for group in groups
    ]
    plt.figure(figsize=(9, 5))
    plt.bar(groups, group_acc, color="#4C78A8")
    plt.ylim(0, 1)
    plt.title("Exact Plan Accuracy by Group")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(outdir / "exact_accuracy_by_group.png")
    plt.close()

    categories = sorted({t.get("category", "unknown") for t in traces})
    cat_acc = [
        _mean([t.get("metrics", {}).get("exact_plan_match", 0) for t in traces if t.get("category") == category])
        for category in categories
    ]
    plt.figure(figsize=(12, 5))
    plt.bar(categories, cat_acc, color="#72B7B2")
    plt.ylim(0, 1)
    plt.title("Exact Plan Accuracy by Category")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(outdir / "exact_accuracy_by_category.png")
    plt.close()

    precision = []
    recall = []
    f1 = []
    for agent in AGENT_NAMES:
        tp = fp = fn = 0
        for trace in traces:
            metrics = trace.get("metrics", {})
            expected = metrics.get(f"expected_{agent}", 0)
            predicted = metrics.get(f"predicted_{agent}", 0)
            if expected and predicted:
                tp += 1
            elif not expected and predicted:
                fp += 1
            elif expected and not predicted:
                fn += 1
        p = _safe_div(tp, tp + fp)
        r = _safe_div(tp, tp + fn)
        precision.append(p)
        recall.append(r)
        f1.append(_safe_div(2 * p * r, p + r))

    x = np.arange(len(AGENT_NAMES))
    width = 0.25
    plt.figure(figsize=(10, 5))
    plt.bar(x - width, precision, width=width, label="Precision", color="#4C78A8")
    plt.bar(x, recall, width=width, label="Recall", color="#72B7B2")
    plt.bar(x + width, f1, width=width, label="F1", color="#E45756")
    plt.xticks(x, AGENT_NAMES, rotation=20, ha="right")
    plt.ylim(0, 1)
    plt.legend()
    plt.title("Agent-Level Precision / Recall / F1")
    plt.tight_layout()
    plt.savefig(outdir / "agent_precision_recall_f1.png")
    plt.close()

    failure_counts: dict[str, int] = {}
    for trace in traces:
        reason = trace.get("failure_reason", "unknown")
        failure_counts[reason] = failure_counts.get(reason, 0) + 1
    plt.figure(figsize=(9, 5))
    plt.bar(list(failure_counts.keys()), list(failure_counts.values()), color="#F58518")
    plt.title("Failure Reason Distribution")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(outdir / "failure_reason_distribution.png")
    plt.close()

    first_agents = AGENT_NAMES + ["none"]
    heat = np.zeros((len(first_agents), len(first_agents)), dtype=int)
    index = {name: idx for idx, name in enumerate(first_agents)}
    for trace in traces:
        expected_first = trace.get("expected_agents", [None])[0] if trace.get("expected_agents") else "none"
        predicted_first = trace.get("predicted_agents", [None])[0] if trace.get("predicted_agents") else "none"
        expected_first = expected_first if expected_first in index else "none"
        predicted_first = predicted_first if predicted_first in index else "none"
        heat[index[expected_first], index[predicted_first]] += 1
    np.savetxt(outdir / "first_agent_confusion_heatmap.csv", heat, fmt="%d", delimiter=",")
    plt.figure(figsize=(7, 6))
    plt.imshow(heat, cmap="Blues", aspect="auto")
    plt.colorbar()
    plt.xticks(range(len(first_agents)), first_agents, rotation=25, ha="right")
    plt.yticks(range(len(first_agents)), first_agents)
    plt.title("Expected vs Predicted First Agent")
    plt.tight_layout()
    plt.savefig(outdir / "first_agent_confusion_heatmap.png")
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="evaluation_outputs/operator_routing")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--queries-file", default=None)
    parser.add_argument("--only-query-id", default=None)
    parser.add_argument("--no-plots", action="store_true")
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
        traces.append(run_single_case(case))

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
