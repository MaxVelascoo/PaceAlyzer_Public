import re
import time
import json
from agents.state import AgentState
from services.rag_service import rag_service
from llm.client import client, MODEL
from services.context_service import format_context_for_prompt
from utils.logger import logger


QUERY_GENERATION_PROMPT = """Eres el agente Librarian de PaceAlyzer, un sistema de planificación de entrenamientos ciclistas.
Tu tarea es generar una query semántica estructurada para buscar en una biblioteca de plantillas de entrenamiento.

La query debe seguir EXACTAMENTE el mismo formato que los textos de embedding de las plantillas,
para maximizar la similitud coseno entre la query y los documentos relevantes.

═══ FORMATO DE SALIDA (obligatorio) ═══

SUMMARY: [1-2 frases describiendo la sesión deseada: objetivo fisiológico, zona de trabajo, estructura, contexto de fatiga]

RELATED_CONCEPTS: [conceptos relevantes en español e inglés separados por coma]

SEMANTIC_LABELS:
primary_goal=[valor]
secondary_goals=[valores separados por coma, o vacío]
work_zone=[valor]
structure_type=[valor]
fatigue_suitability=[valor]
load_level=[valor]
duration_class=[valor si se conoce, u omitir]

═══ TAXONOMÍA (usa EXACTAMENTE estos valores) ═══

primary_goal:
  recovery | endurance | tempo | sweetspot | threshold | vo2max |
  anaerobic_frc | neuromuscular_sprint | strength_torque | activation_pre_race | mixed

work_zone:
  Z1 | Z2 | Z3 | Z3_Z4 | Z4 | Z4_Z5 | Z5 | Z6_Z7 | mixed

structure_type:
  steady | long_intervals | short_intervals | microbursts | sprints |
  torque_sprints | over_under | pyramid_ladder | mixed

fatigue_suitability:
  very_fatigued_ok | fatigued_ok | normal_or_fresh | fresh_only

load_level:
  very_low | low | medium | high | very_high

duration_class:
  very_short | short | medium | long | very_long

═══ REGLAS DE INTERPRETACIÓN ═══

Del mensaje del usuario:
- "umbral", "FTP", "threshold" → primary_goal=threshold, work_zone=Z4
- "VO2max", "aeróbico máximo", "intervals" cortos alta intensidad → primary_goal=vo2max, work_zone=Z5
- "sweetspot", "subumbral" → primary_goal=sweetspot, work_zone=Z3_Z4
- "fondo", "base", "endurance", "Z2" → primary_goal=endurance, work_zone=Z2
- "tempo" → primary_goal=tempo, work_zone=Z3
- "recuperación", "recovery", "soltar piernas" → primary_goal=recovery, work_zone=Z1, fatigue_suitability=very_fatigued_ok
- "sprint", "explosivo", "neuromuscular" → primary_goal=neuromuscular_sprint, work_zone=Z6_Z7
- "FRC", "anaeróbico", "lactato", "punch", "ataques" → primary_goal=anaerobic_frc, work_zone=Z6_Z7
- "fuerza", "torque", "baja cadencia" → primary_goal=strength_torque, work_zone=Z6_Z7
- "activación", "opener", "pre-carrera" → primary_goal=activation_pre_race

Del TSB del atleta:
- TSB > +10 → fatigue_suitability=fresh_only o normal_or_fresh (apto para sesiones duras)
- TSB entre -10 y +10 → fatigue_suitability=normal_or_fresh
- TSB entre -20 y -10 → fatigue_suitability=fatigued_ok (preferir sesiones moderadas)
- TSB < -20 → fatigue_suitability=very_fatigued_ok (solo recuperación o endurance suave)

De señales de bienestar (HRV/FC reposo):
- Señal negativa → reducir fatigue_suitability al nivel más bajo, aunque el TSB sea positivo
- Señal positiva → mantener o aumentar

IMPORTANTE: NO incluyas valores numéricos de FTP, TSS, CTL, ATL, TSB, ni duración exacta en minutos.
Usa categorías semánticas en SEMANTIC_LABELS y lenguaje natural en SUMMARY y RELATED_CONCEPTS.

═══ EJEMPLO ═══

Petición: "dame un entreno de umbral para hoy" | TSB: +8

SUMMARY: Sesión de ciclismo orientada a desarrollar el umbral funcional de potencia mediante intervalos largos en Z4. El atleta está en forma normal, apto para carga media-alta.

RELATED_CONCEPTS: threshold, FTP, umbral, Z4, sustained power, cruise intervals, pacing, lactate tolerance

SEMANTIC_LABELS:
primary_goal=threshold
secondary_goals=ftp,pacing,lactate_tolerance
work_zone=Z4
structure_type=long_intervals
fatigue_suitability=normal_or_fresh
load_level=high
duration_class=medium"""


def _generate_rag_query(state: AgentState) -> str:
    """Usa el LLM para generar un query text semánticamente rico para el RAG."""
    user_message = state.get("message", "")
    athlete_context = state.get("athlete_context") or {}

    # Instrucción del Operator
    operator_instruction = ""
    for step in state.get("operator_plan", []):
        if step.get("agent") in ("librarian", "workout_editor"):
            operator_instruction = step.get("instruction", "")
            break

    context_summary = format_context_for_prompt(athlete_context) if athlete_context else ""

    # NO incluir duración objetivo - queremos query general
    user_content = f"""Mensaje del usuario: "{user_message}"
Instrucción del planificador: "{operator_instruction}"
{context_summary}"""

    try:
        t0 = time.monotonic()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": QUERY_GENERATION_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            max_completion_tokens=300,  # Query estructurada, necesita más tokens
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        query = response.choices[0].message.content.strip()
        logger.llm_call(
            "LibraryAgent",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            duration_ms,
        )
        logger.agent_end("LibraryAgent.query_gen", 0, {"query": query})
        return query
    except Exception as e:
        logger.error("LibraryAgent", f"Query generation failed: {e}")
        # Fallback: usar el mensaje del usuario directamente
        return user_message or "entreno ciclismo"


def _extract_target_duration(state: AgentState) -> int:
    """
    Intenta extraer la duración objetivo de la instrucción del Operator.
    Fallback: usa el TSB y el volumen semanal para estimar una duración apropiada.
    """
    for step in state.get("operator_plan", []):
        if step.get("agent") in ("librarian", "workout_editor"):
            instruction = step.get("instruction", "")
            logger.agent_start("LibraryAgent.duration_extract", {"instruction": instruction[:100]})
            # Buscar patrones como "60min", "90 min", "1h30", "1.5h"
            m = re.search(r'(\d+)\s*min', instruction, re.IGNORECASE)
            if m:
                duration = int(m.group(1))
                logger.agent_end("LibraryAgent.duration_extract", 0, {"source": "operator_instruction", "duration": duration})
                return duration
            m = re.search(r'(\d+(?:\.\d+)?)\s*h(?:oras?)?', instruction, re.IGNORECASE)
            if m:
                duration = int(float(m.group(1)) * 60)
                logger.agent_end("LibraryAgent.duration_extract", 0, {"source": "operator_instruction_hours", "duration": duration})
                return duration

    # Fallback: estimar duración basada en TSB y volumen semanal
    ctx = state.get("athlete_context") or {}
    tsb = ctx.get("tsb")
    hours_avg = ctx.get("hours_avg_4w")
    
    # Duración base: 20% del volumen semanal (asumiendo 5 sesiones/semana)
    # Esto da duraciones más realistas que dividir entre 7 días
    if hours_avg:
        base_duration = int((hours_avg * 60) * 0.20)  # 20% del volumen semanal
    else:
        base_duration = 90  # default 90 min
    
    # Ajustar según TSB
    if tsb is not None:
        if tsb > 10:
            # Muy recuperado: sesión larga/intensa (120-150% de la base)
            duration = int(base_duration * 1.35)
        elif tsb > 0:
            # Recuperado: sesión normal (100-120% de la base)
            duration = int(base_duration * 1.10)
        elif tsb > -10:
            # Neutral: sesión moderada (80-100% de la base)
            duration = int(base_duration * 0.90)
        elif tsb > -20:
            # Fatigado: sesión corta (60-80% de la base)
            duration = int(base_duration * 0.70)
        else:
            # Muy fatigado: recuperación (40-60% de la base)
            duration = int(base_duration * 0.50)
    else:
        duration = base_duration
    
    # Limitar a rangos razonables. En fatiga alta el límite superior es duro:
    # una sesión "de recuperación" no debería convertirse en 90-120 min solo
    # porque el volumen semanal previo sea alto.
    if tsb is not None and tsb <= -20:
        duration = max(25, min(60, duration))
    elif tsb is not None and tsb <= -10:
        duration = max(35, min(90, duration))
    else:
        duration = max(45, min(180, duration))
    
    logger.agent_end("LibraryAgent.duration_extract", 0, {
        "source": "tsb_adjusted",
        "hours_avg_4w": hours_avg,
        "tsb": tsb,
        "base_duration": base_duration if hours_avg else 90,
        "adjusted_duration": duration
    })
    return duration


def _estimate_target_tss(athlete_context: dict) -> float:
    """
    Estima el TSS objetivo basado en TSB y volumen semanal.
    No asume que todos los días son iguales.
    """
    tss_avg = athlete_context.get("tss_avg_4w")
    tsb = athlete_context.get("tsb")
    
    # TSS base: 20% del volumen semanal (asumiendo 5 sesiones/semana)
    if tss_avg:
        base_tss = float(tss_avg) * 0.20
    else:
        base_tss = 70.0
    
    # Ajustar según TSB
    if tsb is not None:
        if tsb > 10:
            # Muy recuperado: sesión intensa (130-150% de la base)
            target_tss = base_tss * 1.40
        elif tsb > 0:
            # Recuperado: sesión normal-alta (110-130% de la base)
            target_tss = base_tss * 1.20
        elif tsb > -10:
            # Neutral: sesión moderada (90-110% de la base)
            target_tss = base_tss * 1.00
        elif tsb > -20:
            # Fatigado: sesión ligera (60-90% de la base)
            target_tss = base_tss * 0.75
        else:
            # Muy fatigado: recuperación (30-60% de la base)
            target_tss = base_tss * 0.45
    else:
        target_tss = base_tss
    
    if tsb is not None and tsb <= -20:
        target_tss = min(target_tss, 35.0)
    elif tsb is not None and tsb <= -10:
        target_tss = min(target_tss, 60.0)

    logger.agent_start("LibraryAgent.tss_estimate", {
        "tss_avg_4w": tss_avg,
        "tsb": tsb,
        "base_tss": round(base_tss, 1),
        "target_tss": round(target_tss, 1)
    })
    
    return target_tss


def _extract_session_type(state: AgentState) -> str:
    """
    Usa el mensaje original del usuario como contexto de sesión para el RAG.
    Es más semánticamente rico que la instrucción del Operator.
    """
    # El mensaje del usuario es lo más relevante para la búsqueda semántica
    user_message = state.get("message", "")
    if user_message:
        return user_message
    # Fallback: instrucción del Operator
    for step in state.get("operator_plan", []):
        if step.get("agent") in ("librarian", "workout_editor"):
            return step.get("instruction", "")
    return ""


def run(state: AgentState) -> AgentState:
    """
    Nodo RAG puro — solo recupera plantillas y las deposita en el AgentState.
    NO llama al LLM, NO persiste, NO modifica otros campos del state.
    """
    t0 = time.monotonic()
    logger.agent_start("LibraryAgent", {
        "date": state.get("date"),
        "has_context": state.get("athlete_context") is not None,
    })

    athlete_context = state.get("athlete_context") or {}
    target_duration_min = _extract_target_duration(state)
    target_tss = _estimate_target_tss(athlete_context)

    # Generar query text semánticamente rico con LLM (sin incluir duración para query más general)
    session_type = _generate_rag_query(state)
    logger.agent_end("LibraryAgent", 0, {"rag_query": session_type, "target_duration_min": target_duration_min})

    templates = rag_service.search(
        athlete_context=athlete_context,
        target_duration_min=target_duration_min,
        target_tss=target_tss,
        session_type=session_type,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)

    if templates:
        # Log top 3 entrenamientos recuperados (título y duración)
        top3_info = {}
        for i, t in enumerate(templates[:3], 1):
            title = t.get("title", "Sin título")
            duration = t.get("duration_min", 0)
            top3_info[f"top{i}"] = f"{title} ({duration}min)"
        
        logger.agent_end("LibraryAgent", duration_ms, {
            "templates_found": len(templates),
            "template_ids": [t.get("id") for t in templates],
            "target_duration_min": target_duration_min,
            "target_tss": target_tss,
            **top3_info,
        })
        return {**state, "rag_templates": templates}
    else:
        logger.error("LibraryAgent", f"No templates found with similarity >= 0.55 after reranking — workout_editor will generate from scratch")
        return {**state, "rag_templates": None}
