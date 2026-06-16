import json
import re
import time
from datetime import date, timedelta
from agents.state import AgentState
from llm.client import client, MODEL
from tools.registry import registry
from services.context_service import format_context_for_prompt
from services.rag_service import rag_service
from services.tss_estimator import estimate_tss
from services.nutrition_utils import resolve_nutrition
from utils.logger import logger


# ── Prompt de planificación (decide qué tipo de sesión va cada día) ───────────

PLANNER_PROMPT = """Eres un planificador de entrenamientos ciclistas de élite.
Tu tarea es decidir QUÉ TIPO de sesión va en cada día de la semana, sin generar la estructura detallada.

Recibirás el contexto del atleta y debes devolver un plan de sesiones con:
- La fecha de cada día de entrenamiento
- El tipo de sesión (familia: recovery, endurance, tempo, sweetspot, threshold, vo2max, anaerobic, neuromuscular)
- La duración estimada en minutos
- El TSS estimado

REGLAS DE PLANIFICACIÓN:
- Respeta el número de días disponibles del atleta (available_days)
- No pongas dos días de alta intensidad (threshold, vo2max, anaerobic) seguidos
- Adapta la intensidad al TSB: si TSB < -20, semana de recuperación
- Si hay evento próximo (<14 días): semana de puesta a punto (reducir carga 30-40%)
- Si hay evento próximo (14-30 días): semana de carga alta
- Incluye siempre al menos 1 día de recovery o endurance
- La duración total debe ser coherente con el promedio de las últimas 4 semanas
- NO incluyas días bloqueados ni días con status "modified"
- Si hay señal HRV/FC reposo negativa, reducir intensidad general de la semana

FORMATO DE RESPUESTA:
{
  "session_plan": [
    {
      "date": "YYYY-MM-DD",
      "session_family": "threshold",
      "duration_min": 120,
      "target_tss": 95,
      "rationale": "TSB positivo, día de carga principal"
    }
  ]
}

Responde SOLO con JSON válido."""


# ── Prompt de adaptación (adapta plantillas RAG a cada día) ──────────────────

ADAPTER_PROMPT = """Eres un editor de entrenamientos ciclistas.
Para cada día del plan semanal, recibirás una plantilla de referencia del catálogo y debes adaptarla al atleta.

INSTRUCCIONES:
- Adapta las zonas de potencia al FTP real del atleta (los targets son relativos)
- Ajusta la duración si es necesario para que coincida con el target_duration_min
- Ajusta el número de series según el TSB y la carga objetivo
- Mantén la estructura general de la plantilla
- Si no hay plantilla disponible para un día, genera el entreno desde cero

TÍTULOS:
- Usa el título de la plantilla de referencia tal cual, sin modificarlo
- NO añadas palabras como "Adaptado", "Modificado", "Ajustado" ni similares
- Si no hay plantilla, crea un título descriptivo y conciso (máximo 40 caracteres)

CAMPOS OBLIGATORIOS por día:
- date, title, description, planned_duration_s, structure, template_id (si usaste plantilla)

FORMATO DE RESPUESTA:
{
  "week_plan": [
    {
      "date": "YYYY-MM-DD",
      "title": "Nombre del entreno",
      "description": "Descripción breve",
      "planned_duration_s": 7200,
      "template_id": "uuid-o-null",
      "structure": { ... }
    }
  ]
}

Responde SOLO con JSON válido."""


def _calculate_duration(structure: dict) -> int:
    """Calcula la duración total en segundos expandiendo repeats."""
    def walk(steps: list) -> int:
        total = 0
        for step in steps:
            if step.get("type") == "interval":
                total += step.get("duration_s", 0)
            elif step.get("type") == "repeat":
                total += step.get("repeat", 1) * walk(step.get("steps", []))
        return total
    return walk(structure.get("steps", []))


def _parse_week_range(instruction: str) -> tuple[str, str] | tuple[None, None]:
    """Extrae el rango de fechas YYYY-MM-DD de la instrucción del Operator."""
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', instruction)
    if len(dates) >= 2:
        return dates[0], dates[1]
    if len(dates) == 1:
        start = date.fromisoformat(dates[0])
        end = start + timedelta(days=6)
        return start.isoformat(), end.isoformat()
    return None, None


def _get_instruction(state: AgentState) -> str | None:
    for step in state.get("operator_plan", []):
        if step.get("agent") == "week_planner":
            return step.get("instruction")
    return None


# ── Mapeo de familia de sesión a query RAG ────────────────────────────────────

FAMILY_TO_RAG_QUERY = {
    "recovery":      "ciclismo recuperación activa Z1 Z2 suave",
    "endurance":     "ciclismo fondo aeróbico Z2 base resistencia",
    "tempo":         "ciclismo tempo Z3 ritmo sostenido moderado",
    "sweetspot":     "ciclismo sweetspot Z3 Z4 umbral moderado",
    "threshold":     "ciclismo umbral threshold Z4 intervalos potencia",
    "vo2max":        "ciclismo VO2max Z5 intervalos cortos alta intensidad",
    "anaerobic":     "ciclismo anaeróbico Z6 sprints lactato alta carga",
    "neuromuscular": "ciclismo neuromuscular Z7 sprints explosividad potencia",
}


def run(state: AgentState) -> AgentState:
    """
    Nodo LangGraph: genera el plan semanal en dos fases.

    Fase 1 — Planificación: el LLM decide qué tipo de sesión va cada día
             (familia, duración, TSS objetivo) sin generar estructura detallada.

    Fase 2 — RAG + Adaptación: para cada día planificado, busca la mejor
             plantilla en la biblioteca y pide al LLM que la adapte al atleta.
             Si no hay plantilla, genera desde cero.
    """
    instruction = _get_instruction(state)
    if not instruction:
        logger.agent_skip("WeekPlannerAgent", "no instruction from Operator")
        return state

    logger.agent_start("WeekPlannerAgent", {
        "instruction": instruction[:80],
        "date": state["date"],
    })
    t0 = time.monotonic()

    # ── Determinar rango de la semana ─────────────────────────────────────────
    week_start_str, week_end_str = _parse_week_range(instruction)
    if not week_start_str:
        ref = date.fromisoformat(state["date"])
        week_start = ref - timedelta(days=ref.weekday())
        week_start_str = week_start.isoformat()
        week_end_str = (week_start + timedelta(days=6)).isoformat()

    # ── Leer entrenos existentes y días bloqueados ────────────────────────────
    week_result = registry.execute("get_week_workouts", {
        "user_id": state["user_id"],
        "week_start": week_start_str,
        "week_end": week_end_str,
    })
    existing_workouts: list[dict] = week_result.data.get("workouts", []) if week_result.success else []

    blocked_result = registry.execute("get_blocked_days", {
        "user_id": state["user_id"],
        "week_start": week_start_str,
        "week_end": week_end_str,
    })
    blocked_days: dict[str, str] = {
        r["date"]: (r.get("reason") or "bloqueado")
        for r in (blocked_result.data.get("blocked_days", []) if blocked_result.success else [])
    }

    locked_dates = {w["date"] for w in existing_workouts if w.get("status") == "modified"}
    locked_dates |= set(blocked_days.keys())
    existing_by_date = {w["date"]: w for w in existing_workouts}

    # ── Construir contexto para el planificador ───────────────────────────────
    existing_summary = []
    for w in existing_workouts:
        locked = " [BLOQUEADO - no modificar]" if w["date"] in locked_dates else ""
        dur_min = (w.get("planned_duration_s") or 0) // 60
        existing_summary.append(f"  - {w['date']}: {w['title']} ({dur_min}min, status={w['status']}){locked}")

    existing_text = (
        "Entrenos ya existentes:\n" + "\n".join(existing_summary)
        if existing_summary else "No hay entrenos planificados aún."
    )
    locked_text = (
        f"Fechas BLOQUEADAS (no generar): {', '.join(sorted(locked_dates))}"
        if locked_dates else "No hay fechas bloqueadas."
    )
    if blocked_days:
        locked_text += "\n" + ", ".join(f"{d} ({r})" for d, r in sorted(blocked_days.items()))

    athlete_text = format_context_for_prompt(state["athlete_context"]) if state.get("athlete_context") else ""

    planner_prompt = f"""{athlete_text}

Semana: {week_start_str} al {week_end_str}
{existing_text}
{locked_text}

Instrucción: {instruction}"""

    # ════════════════════════════════════════════════════════════════════════
    # FASE 1: Planificación — qué tipo de sesión va cada día
    # ════════════════════════════════════════════════════════════════════════
    logger.agent_start("WeekPlannerAgent.phase1_planning", {"prompt_len": len(planner_prompt)})

    plan_response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": planner_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_completion_tokens=800,
    )
    session_plan: list[dict] = json.loads(plan_response.choices[0].message.content).get("session_plan", [])

    logger.agent_end("WeekPlannerAgent.phase1_planning", 0, {
        "days_planned": len(session_plan),
        "sessions": [(s["date"], s["session_family"]) for s in session_plan],
    })

    # ════════════════════════════════════════════════════════════════════════
    # FASE 2: RAG por cada día + adaptación
    # ════════════════════════════════════════════════════════════════════════
    athlete_context = state.get("athlete_context") or {}
    ftp = athlete_context.get("ftp")

    days_with_templates = []
    for session in session_plan:
        day_date = session.get("date")
        if not day_date or day_date in locked_dates:
            continue

        family = session.get("session_family", "endurance")
        duration_min = session.get("duration_min", 90)
        target_tss = session.get("target_tss", 70)
        rag_query = FAMILY_TO_RAG_QUERY.get(family, f"ciclismo {family} entrenamiento")

        # Búsqueda RAG para este día
        templates = rag_service.search(
            athlete_context=athlete_context,
            target_duration_min=duration_min,
            target_tss=float(target_tss),
            session_type=rag_query,
        )

        best_template = templates[0] if templates else None
        logger.agent_start("WeekPlannerAgent.rag", {
            "date": day_date,
            "family": family,
            "template": best_template.get("title") if best_template else "none (generate from scratch)",
        })

        days_with_templates.append({
            "session": session,
            "template": best_template,
        })

    # ── Construir prompt de adaptación ───────────────────────────────────────
    days_json = []
    for item in days_with_templates:
        session = item["session"]
        template = item["template"]
        entry = {
            "date": session["date"],
            "session_family": session["session_family"],
            "target_duration_min": session["duration_min"],
            "target_tss": session["target_tss"],
            "rationale": session.get("rationale", ""),
        }
        if template:
            entry["reference_template"] = {k: v for k, v in template.items() if k != "embedding"}
        days_json.append(entry)

    adapter_user_prompt = f"""{athlete_text}

Días a generar:
{json.dumps(days_json, ensure_ascii=False, indent=2)}

Genera la estructura completa para cada día adaptando la plantilla de referencia al atleta.
Si no hay plantilla de referencia, genera el entreno desde cero."""

    logger.agent_start("WeekPlannerAgent.phase2_adaptation", {"days": len(days_json)})

    adapt_response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": ADAPTER_PROMPT},
            {"role": "user", "content": adapter_user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_completion_tokens=4000,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.llm_call(
        "WeekPlannerAgent",
        plan_response.usage.prompt_tokens + adapt_response.usage.prompt_tokens,
        plan_response.usage.completion_tokens + adapt_response.usage.completion_tokens,
        duration_ms,
    )

    week_plan: list[dict] = json.loads(adapt_response.choices[0].message.content).get("week_plan", [])
    logger.agent_end("WeekPlannerAgent.phase2_adaptation", 0, {"days_generated": len(week_plan)})

    # ── Persistir cada día ────────────────────────────────────────────────────
    actions = list(state.get("actions_taken", []))
    week_plan_summary: list[dict] = []
    saved = 0
    skipped = 0

    for day in week_plan:
        day_date = day.get("date")
        if not day_date:
            continue

        if day_date in locked_dates:
            logger.agent_skip("WeekPlannerAgent", f"date {day_date} is locked")
            skipped += 1
            continue

        if "structure" in day:
            day["planned_duration_s"] = _calculate_duration(day["structure"])
            if ftp:
                tss = estimate_tss(day["structure"], float(ftp))
                if tss is not None:
                    day["estimated_tss"] = tss

        # Limpiar título: eliminar sufijos como "Adaptado", "Modificado", etc.
        if day.get("title"):
            import re as _re
            day["title"] = _re.sub(
                r'\s*[\|\-–]\s*(Adaptado|Modificado|Ajustado|Adapted|Modified).*$',
                '', day["title"], flags=_re.IGNORECASE
            ).strip()

        # Resolver nutrition desde la plantilla RAG del día (si existe)
        template_for_day = next(
            (item["template"] for item in days_with_templates if item["session"]["date"] == day_date),
            None,
        )
        nutrition_template = template_for_day.get("nutrition_template") if template_for_day else None
        resolved_nutrition = resolve_nutrition(
            nutrition_from_llm=day.get("nutrition"),
            nutrition_template=nutrition_template,
            athlete_context=athlete_context,
        )
        if resolved_nutrition:
            day["nutrition"] = resolved_nutrition

        day["status"] = "planned"
        day["source"] = "system"

        if day_date in existing_by_date:
            workout_id = existing_by_date[day_date]["id"]
            fields = {k: v for k, v in day.items() if k not in ("date", "source")}
            result = registry.execute("update_workout", {"workout_id": workout_id, "changes": fields})
        else:
            fields = {k: v for k, v in day.items() if k != "date"}
            result = registry.execute("insert_workout", {
                "user_id": state["user_id"],
                "date": day_date,
                "fields": fields,
            })

        if result.success:
            saved += 1
            actions.append(f"week_plan_saved:{day_date}")
            week_plan_summary.append({
                "date": day_date,
                "title": day.get("title", ""),
                "duration_min": (day.get("planned_duration_s") or 0) // 60,
                "estimated_tss": day.get("estimated_tss"),
                "template_id": day.get("template_id"),
            })
        else:
            logger.error("WeekPlannerAgent", f"Error guardando {day_date}: {result.error}")

    logger.agent_end("WeekPlannerAgent", duration_ms, {
        "week": f"{week_start_str} → {week_end_str}",
        "saved": saved,
        "skipped": skipped,
        "locked": len(locked_dates),
        "rag_used": sum(1 for d in days_with_templates if d["template"]),
        "generated_from_scratch": sum(1 for d in days_with_templates if not d["template"]),
    })

    return {
        **state,
        "actions_taken": actions,
        "week_plan_summary": week_plan_summary,
    }
