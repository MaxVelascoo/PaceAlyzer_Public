"""Evaluación end-to-end del chat multiagente (Experimento C).

Ejecuta queries reales contra el grafo completo o contra /api/chat, valida la
respuesta final y comprueba los efectos persistidos en Supabase.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

try:
    import yaml
except Exception:
    yaml = None

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

_script_path = Path(__file__).resolve()
_backend_app = _script_path.parents[2] / "app"
if str(_backend_app) not in sys.path:
    sys.path.insert(0, str(_backend_app))

LOG = logging.getLogger("evaluate_end_to_end")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

DEFAULT_OUTPUT_ROOT = _script_path.parent / "evaluation_outputs" / "end_to_end"
DEFAULT_SYNTHETIC_USER_ID = "00000000-0000-4000-8000-00000000e2e1"


@dataclass
class E2ECase:
    id: str
    category: str
    date: str
    messages: list[str]
    expected: dict[str, Any]
    setup_context: dict[str, Any] = field(default_factory=dict)
    setup_workouts: list[dict[str, Any]] = field(default_factory=list)
    notes: str | None = None


def _repo_root() -> Path:
    return _script_path.parents[3]


def load_cases(path: str | None = None) -> list[E2ECase]:
    if yaml is None:
        raise RuntimeError("PyYAML no está instalado. Instala pyyaml o ejecuta dentro del venv del backend.")

    queries_path = Path(path) if path else _repo_root() / "evaluation" / "end_to_end_eval_queries.yaml"
    with open(queries_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    items = raw.get("cases", raw) if isinstance(raw, dict) else raw
    return [E2ECase(**item) for item in items]


def _date_range(start: str, end: str) -> list[str]:
    day = datetime.fromisoformat(start).date()
    end_day = datetime.fromisoformat(end).date()
    dates = []
    while day <= end_day:
        dates.append(day.isoformat())
        day += timedelta(days=1)
    return dates


def _simple_structure(duration_min: int, zone: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "sport": "cycling",
        "steps": [
            {
                "type": "warmup",
                "duration_s": 600,
                "target": {"zone": "Z1-Z2"},
                "description": "Calentamiento progresivo.",
            },
            {
                "type": "steady",
                "duration_s": max(600, int(duration_min * 60) - 1200),
                "target": {"zone": zone},
                "description": f"Bloque principal en {zone}.",
            },
            {
                "type": "cooldown",
                "duration_s": 600,
                "target": {"zone": "Z1"},
                "description": "Vuelta a la calma.",
            },
        ],
    }


def _seed_payload(item: dict[str, Any]) -> dict[str, Any]:
    duration_min = int(item.get("duration_min", 60))
    zone = item.get("zone", "Z2")
    title = item.get("title", f"Seed workout {duration_min}min")
    return {
        "title": title,
        "description": item.get("description", f"Entreno sintético para evaluación end-to-end en {zone}."),
        "planned_duration_s": duration_min * 60,
        "planned_distance_m": None,
        "estimated_tss": item.get("estimated_tss", round(duration_min * 0.7, 1)),
        "status": item.get("status", "planned"),
        "structure": item.get("structure") or _simple_structure(duration_min, zone),
        "nutrition": item.get("nutrition"),
        "source": "user_modified",
    }


def _import_backend_dependencies():
    from db.supabase_client import supabase
    return supabase


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _upsert_rows(supabase, table: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
    if not rows:
        return
    try:
        supabase.table(table).upsert(rows, on_conflict=on_conflict).execute()
    except Exception as upsert_exc:
        # Some Supabase tables may not expose the expected unique constraint in
        # local/staging environments. The caller deletes the target rows first,
        # so insert is a safe fallback.
        try:
            supabase.table(table).insert(rows).execute()
        except Exception as insert_exc:
            sample = rows[0] if rows else {}
            raise RuntimeError(
                f"No se pudieron insertar filas en {table}. "
                f"upsert_error={upsert_exc}; insert_error={insert_exc}; sample_row={sample}"
            ) from insert_exc


def _ensure_user_profile(supabase, user_id: str, setup_context: dict[str, Any]) -> None:
    profile = {
        "id": user_id,
        "ftp": 280,
        "weight": 72.0,
        "max_heartrate": 188,
        "birthdate": "1999-04-15",
        "goal": "evaluación end-to-end de PaceAlyzer",
        "available_days": 5,
    }
    profile.update(setup_context.get("profile") or {})

    try:
        existing = (
            supabase.table("users")
            .select("id")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if existing:
            update_payload = {key: value for key, value in profile.items() if key != "id"}
            supabase.table("users").update(update_payload).eq("id", user_id).execute()
        else:
            supabase.table("users").insert(profile).execute()
    except Exception as exc:
        raise RuntimeError(
            "No se pudo crear/actualizar el usuario sintético. Usa un user_id existente "
            "o revisa constraints/FKs de la tabla public.users."
        ) from exc


def _context_metric_dates(reference_date: str) -> list[str]:
    ref = datetime.fromisoformat(reference_date).date()
    return [(ref - timedelta(days=offset)).isoformat() for offset in range(0, 17)]


def _context_week_starts(reference_date: str) -> list[str]:
    ref = datetime.fromisoformat(reference_date).date()
    current_monday = _monday(ref)
    return [(current_monday - timedelta(weeks=offset)).isoformat() for offset in range(1, 5)]


def _delete_context_rows(supabase, user_id: str, case: E2ECase) -> None:
    for metric_date in _context_metric_dates(case.date):
        try:
            supabase.table("daily_metrics").delete().eq("user_id", user_id).eq("date", metric_date).execute()
        except Exception as exc:
            LOG.warning("No se pudo limpiar daily_metrics en %s: %s", metric_date, exc)

    for week_start in _context_week_starts(case.date):
        try:
            supabase.table("weekly_summaries").delete().eq("user_id", user_id).eq("week_start_date", week_start).execute()
        except Exception as exc:
            LOG.warning("No se pudo limpiar weekly_summaries en %s: %s", week_start, exc)

    try:
        ref = datetime.fromisoformat(case.date).date()
        start = (ref - timedelta(days=7)).isoformat()
        end = (ref + timedelta(days=60)).isoformat()
        supabase.table("events").delete().eq("user_id", user_id).gte("date", start).lte("date", end).execute()
        supabase.table("blocked_days").delete().eq("user_id", user_id).gte("date", start).lte("date", end).execute()
    except Exception as exc:
        LOG.warning("No se pudo limpiar events/blocked_days: %s", exc)


def _build_daily_metric_rows(user_id: str, reference_date: str, setup_context: dict[str, Any]) -> list[dict[str, Any]]:
    ref = datetime.fromisoformat(reference_date).date()
    load = setup_context.get("load") or {}
    wellness = setup_context.get("wellness") or {}

    ctl = float(load.get("ctl", 60))
    atl = float(load.get("atl", 58))
    tsb = float(load.get("tsb", ctl - atl))
    hrv_base = float(wellness.get("hrv_baseline", 72))
    resting_base = int(round(float(wellness.get("resting_hr_baseline", 48))))
    hrv_today = float(wellness.get("hrv_today", hrv_base))
    resting_today = int(round(float(wellness.get("resting_hr_today", resting_base))))

    rows = []
    for offset in range(16, 0, -1):
        day = ref - timedelta(days=offset)
        rows.append({
            "user_id": user_id,
            "date": day.isoformat(),
            "tss": 0,
            "ctl": round(ctl - 1.5 + (offset % 4) * 0.4, 2),
            "atl": round(atl - 1.0 + (offset % 5) * 0.5, 2),
            "tsb": round(tsb + 1.0 - (offset % 3) * 0.5, 2),
            "hrv": round(hrv_base + ((offset % 5) - 2) * 0.8, 1),
            "resting_hr": int(round(resting_base + ((offset % 3) - 1) * 0.6)),
        })
    rows.append({
        "user_id": user_id,
        "date": ref.isoformat(),
        "tss": 0,
        "ctl": ctl,
        "atl": atl,
        "tsb": tsb,
        "hrv": hrv_today,
        "resting_hr": int(resting_today),
    })
    return rows


def _build_weekly_summary_rows(user_id: str, reference_date: str, setup_context: dict[str, Any]) -> list[dict[str, Any]]:
    weekly = setup_context.get("weekly_summary") or {}
    km = float(weekly.get("completed_distance_km", 230))
    hours = float(weekly.get("completed_hours", 9.0))
    tss = float(weekly.get("completed_tss", 500))

    rows = []
    for idx, week_start in enumerate(reversed(_context_week_starts(reference_date))):
        week_start_day = datetime.fromisoformat(week_start).date()
        iso_year, iso_week, _ = week_start_day.isocalendar()
        factor = 0.94 + idx * 0.04
        rows.append({
            "user_id": user_id,
            "week_start_date": week_start,
            "week_end_date": (week_start_day + timedelta(days=6)).isoformat(),
            "iso_year": iso_year,
            "iso_week": iso_week,
            "completed_sessions_count": 4,
            "completed_distance_km": round(km * factor, 1),
            "completed_hours": round(hours * factor, 2),
            "completed_tss": round(tss * factor, 1),
            "ctl_end": round(float((setup_context.get("load") or {}).get("ctl", 60)), 2),
            "atl_end": round(float((setup_context.get("load") or {}).get("atl", 58)), 2),
            "tsb_end": round(float((setup_context.get("load") or {}).get("tsb", 2)), 2),
            "power_zones_minutes": {},
            "hr_zones_minutes": {},
        })
    return rows


def _seed_events_and_blocked_days(supabase, user_id: str, setup_context: dict[str, Any]) -> None:
    events = [
        {"user_id": user_id, **event}
        for event in (setup_context.get("events") or [])
    ]
    blocked_days = [
        {"user_id": user_id, **blocked}
        for blocked in (setup_context.get("blocked_days") or [])
    ]
    if events:
        supabase.table("events").insert(events).execute()
    if blocked_days:
        supabase.table("blocked_days").insert(blocked_days).execute()


def _seed_context(supabase, user_id: str, case: E2ECase) -> None:
    setup_context = case.setup_context or {}
    _ensure_user_profile(supabase, user_id, setup_context)
    _upsert_rows(
        supabase,
        "daily_metrics",
        _build_daily_metric_rows(user_id, case.date, setup_context),
        on_conflict="user_id,date",
    )
    _upsert_rows(
        supabase,
        "weekly_summaries",
        _build_weekly_summary_rows(user_id, case.date, setup_context),
        on_conflict="user_id,iso_year,iso_week",
    )
    _seed_events_and_blocked_days(supabase, user_id, setup_context)


def _clear_chat_history(supabase, user_id: str) -> None:
    try:
        sessions = (
            supabase.table("chat_sessions")
            .select("id")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
        for session in sessions:
            sid = session["id"]
            supabase.table("chat_messages").delete().eq("session_id", sid).execute()
            supabase.table("chat_sessions").delete().eq("id", sid).execute()
    except Exception as exc:
        LOG.warning("No se pudo limpiar historial de chat: %s", exc)


def _delete_workouts_on_dates(supabase, user_id: str, dates: list[str]) -> None:
    for workout_date in sorted(set(dates)):
        try:
            rows = (
                supabase.table("planned_workouts")
                .select("id")
                .eq("user_id", user_id)
                .eq("date", workout_date)
                .execute()
                .data
                or []
            )
            for row in rows:
                supabase.table("planned_workouts").delete().eq("id", row["id"]).eq("user_id", user_id).execute()
        except Exception as exc:
            LOG.warning("No se pudo limpiar planned_workouts en %s: %s", workout_date, exc)


def _case_dates(case: E2ECase) -> list[str]:
    dates = [case.date]
    dates.extend(item["date"] for item in case.setup_workouts if item.get("date"))
    expected = case.expected or {}
    if expected.get("workout_date"):
        dates.append(expected["workout_date"])
    if expected.get("no_workout_dates"):
        dates.extend(expected["no_workout_dates"])
    if expected.get("week_range"):
        dates.extend(_date_range(expected["week_range"][0], expected["week_range"][1]))
    return sorted(set(dates))


def _seed_case(supabase, user_id: str, case: E2ECase) -> None:
    for item in case.setup_workouts:
        workout_date = item["date"]
        payload = {"user_id": user_id, "date": workout_date, **_seed_payload(item)}
        supabase.table("planned_workouts").insert(payload).execute()


def _fetch_workout(supabase, user_id: str, workout_date: str) -> dict[str, Any] | None:
    rows = (
        supabase.table("planned_workouts")
        .select("*")
        .eq("user_id", user_id)
        .eq("date", workout_date)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _fetch_week_workouts(supabase, user_id: str, start: str, end: str) -> list[dict[str, Any]]:
    return (
        supabase.table("planned_workouts")
        .select("*")
        .eq("user_id", user_id)
        .gte("date", start)
        .lte("date", end)
        .order("date")
        .execute()
        .data
        or []
    )


def _call_local(user_id: str, message: str, request_date: str) -> tuple[int, dict[str, Any], dict[str, Any] | None, str | None]:
    from services.orchestrator import handle_message
    from utils.request_metrics import get_request_metrics_collector, clear_request_metrics

    clear_request_metrics()
    try:
        response = handle_message(user_id=user_id, message=message, date=request_date)
        collector = get_request_metrics_collector()
        if collector:
            collector.record_http_status(200)
            summary = collector.build_summary()
        else:
            summary = None
        return 200, response, summary, None
    except Exception as exc:
        collector = get_request_metrics_collector()
        summary = collector.build_summary() if collector else None
        return 500, {}, summary, str(exc)
    finally:
        clear_request_metrics()


def _call_http(base_url: str, user_id: str, message: str, request_date: str) -> tuple[int, dict[str, Any], dict[str, Any] | None, str | None]:
    payload = json.dumps({"user_id": user_id, "message": message, "date": request_date}).encode("utf-8")
    req = urlrequest.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=180) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8")), None, None
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, {}, None, body
    except URLError as exc:
        return 0, {}, None, str(exc)


def _contains_any(workout: dict[str, Any] | None, terms: list[str]) -> bool:
    if not workout:
        return False
    haystack = " ".join(
        str(workout.get(key) or "")
        for key in ["title", "description", "status"]
    ).lower()
    return any(term.lower() in haystack for term in terms)


def _duration_min(workout: dict[str, Any] | None) -> int | None:
    if not workout:
        return None
    duration_s = workout.get("planned_duration_s")
    return int(duration_s // 60) if duration_s else None


def _check_case(
    *,
    case: E2ECase,
    response: dict[str, Any],
    status: int,
    error: str | None,
    summary: dict[str, Any] | None,
    workout: dict[str, Any] | None,
    week_workouts: list[dict[str, Any]],
    no_workout_rows: list[dict[str, Any] | None],
) -> dict[str, Any]:
    expected = case.expected
    checks: dict[str, bool | None] = {}

    checks["http_ok"] = status == 200 and not error
    checks["reply_non_empty"] = len(response.get("reply") or "") >= int(expected.get("min_reply_chars", 1))

    if expected.get("action_in"):
        checks["action_ok"] = response.get("action_taken") in expected["action_in"]
    else:
        checks["action_ok"] = None

    if expected.get("workout_exists") is True:
        checks["workout_exists_ok"] = workout is not None
    elif expected.get("workout_exists") is False:
        checks["workout_exists_ok"] = workout is None
    else:
        checks["workout_exists_ok"] = None

    if expected.get("duration_min_between") and workout:
        lo, hi = expected["duration_min_between"]
        duration = _duration_min(workout)
        checks["duration_ok"] = duration is not None and lo <= duration <= hi
    elif expected.get("duration_min_between"):
        checks["duration_ok"] = False
    else:
        checks["duration_ok"] = None

    if "nutrition_present" in expected:
        has_nutrition = bool(workout and workout.get("nutrition"))
        checks["nutrition_ok"] = has_nutrition is bool(expected["nutrition_present"])
    else:
        checks["nutrition_ok"] = None

    if expected.get("status_in") and workout:
        checks["status_ok"] = workout.get("status") in expected["status_in"]
    elif expected.get("status_in"):
        checks["status_ok"] = False
    else:
        checks["status_ok"] = None

    if expected.get("title_or_description_contains_any"):
        checks["content_ok"] = _contains_any(workout, expected["title_or_description_contains_any"])
    else:
        checks["content_ok"] = None

    if expected.get("week_range"):
        checks["week_count_ok"] = len(week_workouts) >= int(expected.get("min_workouts_in_range", 1))
    else:
        checks["week_count_ok"] = None

    if expected.get("no_workout_dates"):
        checks["no_unwanted_workout_ok"] = all(row is None for row in no_workout_rows)
    else:
        checks["no_unwanted_workout_ok"] = None

    if expected.get("expected_route_contains") and summary:
        route = summary.get("route") or []
        checks["route_ok"] = all(agent in route for agent in expected["expected_route_contains"])
    elif expected.get("expected_route_contains"):
        checks["route_ok"] = None
    else:
        checks["route_ok"] = None

    if "rag_called" in expected and summary:
        checks["rag_ok"] = bool((summary.get("rag") or {}).get("called")) is bool(expected["rag_called"])
    elif "rag_called" in expected:
        checks["rag_ok"] = None
    else:
        checks["rag_ok"] = None

    failed = [name for name, ok in checks.items() if ok is False]
    applicable = [ok for ok in checks.values() if ok is not None]
    overall_success = bool(applicable) and all(applicable)

    return {
        "checks": checks,
        "failed_checks": failed,
        "overall_success": overall_success,
    }


def _summary_metrics(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {
            "request_id": None,
            "route": None,
            "agents_called": None,
            "total_duration_ms": None,
            "llm_calls": None,
            "total_tokens": None,
            "rag_called": None,
            "tool_calls": None,
        }
    return {
        "request_id": summary.get("request_id"),
        "route": ">".join(summary.get("route") or []),
        "agents_called": ">".join(summary.get("agents_called") or []),
        "total_duration_ms": summary.get("total_duration_ms"),
        "llm_calls": (summary.get("llm") or {}).get("calls"),
        "total_tokens": (summary.get("llm") or {}).get("total_tokens"),
        "rag_called": (summary.get("rag") or {}).get("called"),
        "tool_calls": (summary.get("tools") or {}).get("total_calls"),
    }


def run_case(case: E2ECase, *, user_id: str, mode: str, base_url: str, reset: bool) -> dict[str, Any]:
    supabase = _import_backend_dependencies()

    if reset:
        _clear_chat_history(supabase, user_id)
        _delete_context_rows(supabase, user_id, case)
        _delete_workouts_on_dates(supabase, user_id, _case_dates(case))
    _seed_context(supabase, user_id, case)
    _seed_case(supabase, user_id, case)

    steps = []
    final_status = 0
    final_response: dict[str, Any] = {}
    final_summary: dict[str, Any] | None = None
    final_error: str | None = None
    wall_t0 = time.monotonic()

    for message in case.messages:
        t0 = time.monotonic()
        if mode == "local":
            status, response, summary, error = _call_local(user_id, message, case.date)
        else:
            status, response, summary, error = _call_http(base_url, user_id, message, case.date)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        steps.append(
            {
                "message": message,
                "http_status": status,
                "response": response,
                "metrics_summary": summary,
                "wall_duration_ms": elapsed_ms,
                "error": error,
            }
        )
        final_status, final_response, final_summary, final_error = status, response, summary, error

    expected = case.expected
    workout = _fetch_workout(supabase, user_id, expected["workout_date"]) if expected.get("workout_date") else None
    week_workouts = (
        _fetch_week_workouts(supabase, user_id, expected["week_range"][0], expected["week_range"][1])
        if expected.get("week_range")
        else []
    )
    no_workout_rows = [
        _fetch_workout(supabase, user_id, workout_date)
        for workout_date in expected.get("no_workout_dates", [])
    ]

    validation = _check_case(
        case=case,
        response=final_response,
        status=final_status,
        error=final_error,
        summary=final_summary,
        workout=workout,
        week_workouts=week_workouts,
        no_workout_rows=no_workout_rows,
    )

    metrics = _summary_metrics(final_summary)
    return {
        "id": case.id,
        "category": case.category,
        "physiology_scenario": (case.setup_context or {}).get("scenario", "unspecified"),
        "setup_context": case.setup_context,
        "tsb": ((case.setup_context or {}).get("load") or {}).get("tsb"),
        "ctl": ((case.setup_context or {}).get("load") or {}).get("ctl"),
        "atl": ((case.setup_context or {}).get("load") or {}).get("atl"),
        "date": case.date,
        "mode": mode,
        "messages": case.messages,
        "http_status": final_status,
        "action_taken": final_response.get("action_taken"),
        "reply": final_response.get("reply"),
        "error": final_error,
        "wall_duration_ms": int((time.monotonic() - wall_t0) * 1000),
        "workout_after": workout,
        "week_workouts_after": week_workouts,
        "steps": steps,
        **metrics,
        **validation,
    }


def _bool_to_int(value: bool | None) -> int | str:
    if value is None:
        return ""
    return 1 if value else 0


def write_outputs(results: list[dict[str, Any]], outdir: Path, cases: list[E2ECase]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    with open(outdir / "traces.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    csv_fields = [
        "id", "category", "physiology_scenario", "tsb", "ctl", "atl", "date", "mode", "http_status", "action_taken", "overall_success",
        "failed_checks", "wall_duration_ms", "total_duration_ms", "llm_calls", "total_tokens",
        "route", "rag_called", "tool_calls", "reply",
    ]
    check_fields = sorted({key for result in results for key in result["checks"].keys()})

    with open(outdir / "per_query_metrics.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields + check_fields)
        writer.writeheader()
        for result in results:
            row = {field: result.get(field) for field in csv_fields}
            row["failed_checks"] = "|".join(result.get("failed_checks") or [])
            for key in check_fields:
                row[key] = _bool_to_int(result["checks"].get(key))
            writer.writerow(row)

    with open(outdir / "responses.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "category", "physiology_scenario", "message_index", "message", "reply", "action_taken", "http_status", "error"])
        writer.writeheader()
        for result in results:
            for idx, step in enumerate(result["steps"], start=1):
                response = step.get("response") or {}
                writer.writerow({
                    "id": result["id"],
                    "category": result["category"],
                    "physiology_scenario": result["physiology_scenario"],
                    "message_index": idx,
                    "message": step["message"],
                    "reply": response.get("reply"),
                    "action_taken": response.get("action_taken"),
                    "http_status": step["http_status"],
                    "error": step.get("error"),
                })

    errors = [r for r in results if r.get("error") or r.get("failed_checks")]
    with open(outdir / "errors.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "category", "physiology_scenario", "error", "failed_checks", "reply"])
        writer.writeheader()
        for result in errors:
            writer.writerow({
                "id": result["id"],
                "category": result["category"],
                "physiology_scenario": result["physiology_scenario"],
                "error": result.get("error"),
                "failed_checks": "|".join(result.get("failed_checks") or []),
                "reply": result.get("reply"),
            })

    aggregate = build_aggregate(results, cases)
    with open(outdir / "aggregate_metrics.json", "w", encoding="utf-8") as f:
        json.dump(aggregate, f, ensure_ascii=False, indent=2)

    with open(outdir / "aggregate_metrics.md", "w", encoding="utf-8") as f:
        f.write(render_markdown_summary(aggregate))


def build_aggregate(results: list[dict[str, Any]], cases: list[E2ECase]) -> dict[str, Any]:
    total = len(results)
    successes = sum(1 for r in results if r["overall_success"])
    durations = [r["wall_duration_ms"] for r in results if r.get("wall_duration_ms") is not None]
    tokens = [r["total_tokens"] for r in results if isinstance(r.get("total_tokens"), int)]

    by_category = {}
    for category in sorted({case.category for case in cases}):
        rows = [r for r in results if r["category"] == category]
        by_category[category] = {
            "n": len(rows),
            "success_rate": round(sum(1 for r in rows if r["overall_success"]) / len(rows), 3) if rows else 0,
            "avg_wall_duration_ms": round(statistics.mean([r["wall_duration_ms"] for r in rows]), 1) if rows else 0,
        }

    by_physiology_scenario = {}
    for scenario in sorted({r.get("physiology_scenario", "unspecified") for r in results}):
        rows = [r for r in results if r.get("physiology_scenario", "unspecified") == scenario]
        scenario_tokens = [r["total_tokens"] for r in rows if isinstance(r.get("total_tokens"), int)]
        by_physiology_scenario[scenario] = {
            "n": len(rows),
            "success_rate": round(sum(1 for r in rows if r["overall_success"]) / len(rows), 3) if rows else 0,
            "avg_wall_duration_ms": round(statistics.mean([r["wall_duration_ms"] for r in rows]), 1) if rows else 0,
            "avg_total_tokens": round(statistics.mean(scenario_tokens), 1) if scenario_tokens else None,
            "avg_tsb": round(statistics.mean([float(r["tsb"]) for r in rows if r.get("tsb") is not None]), 1) if any(r.get("tsb") is not None for r in rows) else None,
        }

    failure_counts: dict[str, int] = {}
    for result in results:
        for check in result.get("failed_checks") or []:
            failure_counts[check] = failure_counts.get(check, 0) + 1

    routes: dict[str, int] = {}
    for result in results:
        route = result.get("route") or "not_available"
        routes[route] = routes.get(route, 0) + 1

    return {
        "total_cases": total,
        "successful_cases": successes,
        "success_rate": round(successes / total, 3) if total else 0,
        "avg_wall_duration_ms": round(statistics.mean(durations), 1) if durations else 0,
        "median_wall_duration_ms": round(statistics.median(durations), 1) if durations else 0,
        "avg_total_tokens": round(statistics.mean(tokens), 1) if tokens else None,
        "median_total_tokens": round(statistics.median(tokens), 1) if tokens else None,
        "by_category": by_category,
        "by_physiology_scenario": by_physiology_scenario,
        "failure_counts": failure_counts,
        "routes": routes,
    }


def render_markdown_summary(aggregate: dict[str, Any]) -> str:
    lines = [
        "# Experimento C: evaluación end-to-end",
        "",
        f"- Casos evaluados: {aggregate['total_cases']}",
        f"- Casos correctos: {aggregate['successful_cases']}",
        f"- Success rate: {aggregate['success_rate']:.3f}",
        f"- Latencia media wall-clock: {aggregate['avg_wall_duration_ms']:.1f} ms",
        f"- Latencia mediana wall-clock: {aggregate['median_wall_duration_ms']:.1f} ms",
    ]
    if aggregate["avg_total_tokens"] is not None:
        lines.append(f"- Tokens medios por petición final: {aggregate['avg_total_tokens']:.1f}")
    lines.extend(["", "## Resultados por categoría", ""])
    for category, stats in aggregate["by_category"].items():
        lines.append(
            f"- **{category}**: n={stats['n']}, success_rate={stats['success_rate']:.3f}, "
            f"avg_latency={stats['avg_wall_duration_ms']:.1f} ms"
        )
    lines.extend(["", "## Resultados por escenario fisiológico", ""])
    for scenario, stats in aggregate["by_physiology_scenario"].items():
        token_text = f", avg_tokens={stats['avg_total_tokens']:.1f}" if stats["avg_total_tokens"] is not None else ""
        tsb_text = f", avg_tsb={stats['avg_tsb']:.1f}" if stats["avg_tsb"] is not None else ""
        lines.append(
            f"- **{scenario}**: n={stats['n']}, success_rate={stats['success_rate']:.3f}, "
            f"avg_latency={stats['avg_wall_duration_ms']:.1f} ms{token_text}{tsb_text}"
        )
    lines.extend(["", "## Fallos por check", ""])
    if aggregate["failure_counts"]:
        for check, count in sorted(aggregate["failure_counts"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- **{check}**: {count}")
    else:
        lines.append("- No se han detectado fallos automáticos.")
    lines.extend(["", "## Rutas observadas", ""])
    for route, count in sorted(aggregate["routes"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{route}`: {count}")
    lines.append("")
    return "\n".join(lines)


def _savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def generate_figures(results: list[dict[str, Any]], outdir: Path) -> None:
    if plt is None:
        LOG.warning("matplotlib no está instalado; se omiten gráficas.")
        return

    figures = outdir / "figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.22,
    })

    success = sum(1 for r in results if r["overall_success"])
    fail = len(results) - success
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.bar(["Correctas", "Con fallo"], [success, fail], color=["#2E7D5B", "#C75C48"])
    ax.set_ylabel("Número de queries")
    ax.set_ylim(0, max(1, len(results)) + 1)
    for idx, value in enumerate([success, fail]):
        ax.text(idx, value + 0.15, str(value), ha="center", va="bottom")
    _savefig(figures / "e2e_overall_success.png")

    categories = sorted({r["category"] for r in results})
    rates = []
    counts = []
    for category in categories:
        rows = [r for r in results if r["category"] == category]
        rates.append(sum(1 for r in rows if r["overall_success"]) / len(rows))
        counts.append(len(rows))
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.barh(categories, rates, color="#3A6EA5")
    ax.set_xlabel("Tasa de éxito")
    ax.set_xlim(0, 1.05)
    for idx, (rate, count) in enumerate(zip(rates, counts)):
        ax.text(min(1.02, rate + 0.02), idx, f"{rate:.0%} (n={count})", va="center")
    _savefig(figures / "e2e_success_by_category.png")

    scenarios = sorted({r.get("physiology_scenario", "unspecified") for r in results})
    scenario_rates = []
    scenario_counts = []
    for scenario in scenarios:
        rows = [r for r in results if r.get("physiology_scenario", "unspecified") == scenario]
        scenario_rates.append(sum(1 for r in rows if r["overall_success"]) / len(rows))
        scenario_counts.append(len(rows))
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.barh(scenarios, scenario_rates, color="#2F9C95")
    ax.set_xlabel("Tasa de éxito")
    ax.set_xlim(0, 1.05)
    for idx, (rate, count) in enumerate(zip(scenario_rates, scenario_counts)):
        ax.text(min(1.02, rate + 0.02), idx, f"{rate:.0%} (n={count})", va="center")
    _savefig(figures / "e2e_success_by_physiology.png")

    failure_counts: dict[str, int] = {}
    for result in results:
        for check in result.get("failed_checks") or []:
            failure_counts[check] = failure_counts.get(check, 0) + 1
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    if failure_counts:
        labels, values = zip(*sorted(failure_counts.items(), key=lambda item: item[1]))
        ax.barh(labels, values, color="#C75C48")
        ax.set_xlabel("Número de fallos")
    else:
        ax.text(0.5, 0.5, "Sin fallos automáticos", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    _savefig(figures / "e2e_failure_breakdown.png")

    sorted_results = sorted(results, key=lambda r: r["wall_duration_ms"], reverse=True)
    labels = [r["id"] for r in sorted_results]
    values = [r["wall_duration_ms"] / 1000 for r in sorted_results]
    colors = ["#2E7D5B" if r["overall_success"] else "#C75C48" for r in sorted_results]
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("Latencia wall-clock (s)")
    ax.tick_params(axis="x", rotation=45)
    _savefig(figures / "e2e_latency_by_query.png")

    scenario_latency = []
    for scenario in scenarios:
        rows = [r for r in results if r.get("physiology_scenario", "unspecified") == scenario]
        scenario_latency.append(statistics.mean([r["wall_duration_ms"] for r in rows]) / 1000)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(scenarios, scenario_latency, color="#6C7A89")
    ax.set_ylabel("Latencia media wall-clock (s)")
    ax.tick_params(axis="x", rotation=20)
    _savefig(figures / "e2e_latency_by_physiology.png")

    token_rows = [r for r in results if isinstance(r.get("total_tokens"), int)]
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    if token_rows:
        ax.bar([r["id"] for r in token_rows], [r["total_tokens"] for r in token_rows], color="#8A6F3D")
        ax.set_ylabel("Tokens totales")
        ax.tick_params(axis="x", rotation=45)
    else:
        ax.text(0.5, 0.5, "Tokens no disponibles en modo HTTP", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    _savefig(figures / "e2e_tokens_by_query.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evalúa el sistema completo de /api/chat con queries end-to-end.")
    parser.add_argument("--queries-file", default=None, help="Ruta al YAML de casos. Por defecto usa evaluation/end_to_end_eval_queries.yaml")
    parser.add_argument(
        "--user-id",
        default=os.environ.get("PACEALYZER_E2E_USER_ID") or os.environ.get("E2E_TEST_USER_ID") or DEFAULT_SYNTHETIC_USER_ID,
        help=(
            "Usuario sintético usado para el experimento. Si no se indica, usa un UUID fijo de evaluación. "
            "También puede venir de PACEALYZER_E2E_USER_ID."
        ),
    )
    parser.add_argument("--mode", choices=["local", "http"], default="local", help="local invoca el grafo; http llama a /api/chat.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL del backend cuando --mode=http.")
    parser.add_argument("--output-dir", default=None, help="Directorio de salida. Por defecto crea timestamp en evaluation_outputs/end_to_end.")
    parser.add_argument("--no-reset", action="store_true", help="No limpia entrenos/historial de las fechas evaluadas antes de cada caso.")
    parser.add_argument("--skip-figures", action="store_true", help="No genera gráficas.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.user_id:
        raise SystemExit("Falta --user-id o la variable PACEALYZER_E2E_USER_ID con un usuario existente de Supabase.")

    cases = load_cases(args.queries_file)
    outdir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir.mkdir(parents=True, exist_ok=True)

    results = []
    for case in cases:
        LOG.info("Ejecutando %s (%s)", case.id, case.category)
        result = run_case(
            case,
            user_id=args.user_id,
            mode=args.mode,
            base_url=args.base_url,
            reset=not args.no_reset,
        )
        results.append(result)
        status = "OK" if result["overall_success"] else "FAIL"
        LOG.info("%s %s action=%s failed=%s", status, case.id, result.get("action_taken"), result.get("failed_checks"))

    write_outputs(results, outdir, cases)
    if not args.skip_figures:
        generate_figures(results, outdir)

    aggregate = build_aggregate(results, cases)
    print(json.dumps({
        "output_dir": str(outdir.resolve()),
        "total_cases": aggregate["total_cases"],
        "success_rate": aggregate["success_rate"],
        "avg_wall_duration_ms": aggregate["avg_wall_duration_ms"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
