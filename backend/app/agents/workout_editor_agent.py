import json
import time
from agents.state import AgentState
from llm.client import client, MODEL
from tools.registry import registry
from services.context_service import format_context_for_prompt
from services.tss_estimator import estimate_tss
from services.nutrition_utils import resolve_nutrition
from utils.logger import logger


def _calculate_duration(structure: dict) -> int:
    """Calcula la duración total en segundos a partir de la structure, expandiendo repeats."""
    def walk(steps: list) -> int:
        total = 0
        for step in steps:
            if step.get("type") == "interval":
                total += step.get("duration_s", 0)
            elif step.get("type") == "repeat":
                total += step.get("repeat", 1) * walk(step.get("steps", []))
        return total

    return walk(structure.get("steps", []))


def _sanitize_changes_for_db(changes: dict) -> dict:
    """
    Evita cambios que violan constraints de planned_workouts.

    La BD no permite planned_duration_s <= 0. Para peticiones de descanso o
    cancelación el LLM puede devolver structure vacía y duración 0; en ese caso
    persistimos el cambio semántico (status/title/description) sin tocar la
    duración/estructura existente.
    """
    duration = changes.get("planned_duration_s")
    try:
        invalid_duration = duration is not None and int(duration) <= 0
    except (TypeError, ValueError):
        invalid_duration = True

    structure = changes.get("structure")
    empty_structure = isinstance(structure, dict) and not structure.get("steps")

    if invalid_duration or empty_structure:
        changes.pop("planned_duration_s", None)
        changes.pop("structure", None)
        if changes.get("status") not in {"skipped", "completed"}:
            changes["status"] = "skipped"

    return changes


SYSTEM_PROMPT = """Eres un editor de entrenamientos ciclistas.
Recibirás el entreno actual y una instrucción de qué cambiar.
Devuelve SOLO los campos que deben actualizarse en formato JSON.

CAMPOS MODIFICABLES:
- title (string): nombre del entreno
- description (string): descripción breve
- status (string): "planned" | "modified" | "completed" | "skipped"
- planned_duration_s (int): duración total en segundos
- planned_distance_m (int|null): distancia en metros
- structure (object): estructura completa del entreno (ver formato abajo)
- nutrition (object|null): plantilla nutricional con pre/during/post (ver formato abajo)
- template_id (string|null): UUID de la plantilla del catálogo usada como base (solo si se usó una plantilla RAG)

FORMATO EXACTO DE STRUCTURE:
{
  "schema_version": 1,
  "intensity_model": "power_zones",
  "zone_system": "coggan_7",
  "session": {
    "goal": "objetivo del entreno",
    "description": "descripción detallada",
    "execution_notes": ["nota 1"],
    "warnings": ["aviso 1"]
  },
  "steps": [
    {
      "type": "interval",
      "label": "Calentamiento",
      "duration_s": 1200,
      "target": {"zone": "Z2"},
      "instructions": "Cadencia cómoda"
    },
    {
      "type": "repeat",
      "label": "Bloque principal",
      "repeat": 4,
      "steps": [
        {
          "type": "interval",
          "label": "Sprint",
          "duration_s": 10,
          "target": {"zone": "Z6"},
          "instructions": "Máxima explosividad"
        },
        {
          "type": "interval",
          "label": "Recuperación",
          "duration_s": 120,
          "target": {"zone": "Z2"},
          "instructions": "Recuperación activa"
        }
      ]
    },
    {
      "type": "interval",
      "label": "Tempo final",
      "duration_s": 900,
      "target": {"zone": "Z3"},
      "instructions": "Ritmo constante y estable"
    }
  ]
}

FORMATO EXACTO DE NUTRITION:
{
  "pre": {
    "carbs_g_per_kg": 1.5,
    "protein_g_per_kg": 0.2
  },
  "during": {
    "carbs_g_per_hour": 60.0,
    "sodium_mg_per_hour": 500.0
  },
  "post": {
    "carbs_g_per_kg": 1.0,
    "protein_g_per_kg": 0.3
  }
}

ZONAS VÁLIDAS: Z1 (recuperación activa), Z2 (base aeróbica), Z3 (tempo),
               Z4 (umbral), Z5 (VO2max), Z6 (anaeróbico), Z7 (neuromuscular)

REGLAS:
- Si modificas la structure, devuelve la structure COMPLETA, no solo los cambios
- Si solo cambias title/description/status, no incluyas structure en la respuesta
- IMPORTANTE: Si la instrucción implica cambiar la duración del entreno (alargar, acortar, cambiar tiempo),
  DEBES modificar la structure ajustando los duration_s de los pasos correspondientes.
  NO uses planned_duration_s sin structure — siempre deben estar sincronizados.
  planned_duration_s se calcula desde la structure, nunca al revés.
- COHERENCIA DEL TÍTULO: Si el cambio afecta algo que está reflejado en el título (duración, número de series,
  zona, tipo de sesión), actualiza también el título para que sea coherente. Modifica SOLO la parte afectada,
  manteniendo el resto del título intacto. Ejemplos:
  * "EB-08 | Endurance Z2 120min" → alargar a 150min → "EB-08 | Endurance Z2 150min"
  * "TH-01 | 2x10 FTP Express" → cambiar a 3 series → "TH-01 | 3x10 FTP Express"
  * "VO2-02 | 4x4 VO2max clásico" → acortar intervalos a 3min → "VO2-02 | 4x3 VO2max clásico"
  No cambies el código de plantilla (prefijo como EB-08, TH-01) ni partes del título no afectadas.
- Calcula planned_duration_s sumando todos los duration_s (multiplicando por repeat en bloques repeat)
- status siempre debe ser "modified" cuando se edita el entreno
- Si el usuario pide descanso, cancelar o saltarse el entreno, NO devuelvas planned_duration_s=0 ni structure vacía.
  En ese caso cambia status a "skipped" y actualiza title/description.

Responde SOLO con JSON válido con los campos a actualizar:
{"campo": "nuevo_valor", ...}"""


def run(state: AgentState) -> AgentState:
    """Nodo LangGraph: genera los cambios del entreno y los persiste via ToolRegistry."""
    instruction = _get_instruction(state, "workout_editor")
    if not instruction:
        logger.agent_skip("WorkoutEditorAgent", "no instruction from Operator")
        return state

    logger.agent_start("WorkoutEditorAgent", {
        "instruction": instruction[:60],
        "has_workout": state.get("current_workout") is not None,
        "date": state["date"],
    })
    t0 = time.monotonic()

    # Extraer la fecha de la instrucción si el Operator especificó una distinta
    target_date = _extract_date(instruction) or state["date"]

    # Si la fecha objetivo es distinta a la del contexto, leer el entreno de esa fecha
    if target_date != state["date"]:
        from tools.registry import registry as _reg
        plan_result = _reg.execute("get_current_plan", {"user_id": state["user_id"], "date": target_date})
        target_workout = plan_result.data if plan_result.success else None
    else:
        target_workout = state.get("current_workout")

    workout_context = "No hay entreno actual."
    if target_workout:
        w = target_workout
        workout_context = json.dumps({
            "title": w.get("title"),
            "description": w.get("description"),
            "status": w.get("status"),
            "planned_duration_s": w.get("planned_duration_s"),
            "planned_distance_m": w.get("planned_distance_m"),
            "structure": w.get("structure"),
            "nutrition": w.get("nutrition"),
        }, ensure_ascii=False, indent=2)

    # Enriquecimiento RAG: incluir plantillas del catálogo si el librarian las recuperó
    rag_section = ""
    if state.get("rag_templates"):
        import json as _json
        templates_json = _json.dumps(
            [{k: v for k, v in t.items() if k != "embedding"} for t in state["rag_templates"]],
            ensure_ascii=False,
            indent=2,
        )
        rag_section = f"""
PLANTILLAS DE REFERENCIA DEL CATÁLOGO (top-3 más relevantes para este atleta):
{templates_json}

INSTRUCCIONES DE ADAPTACIÓN:
- Elige la plantilla más adecuada según el contexto del atleta y la instrucción
- Ajusta las zonas de potencia al FTP real del atleta (los targets de la plantilla son relativos)
- Adapta la duración si la instrucción lo indica
- Ajusta el número de series/repeticiones según el TSB actual
- Mantén la estructura general de la plantilla elegida

CAMPOS OBLIGATORIOS AL USAR PLANTILLA:
- "template_id": SIEMPRE incluye el "id" de la plantilla elegida
- "nutrition": Copia el "nutrition_template" de la plantilla (el sistema lo convertirá automáticamente)
- "structure": Adapta la "structure" de la plantilla al contexto del atleta
- "title": Usa el título de la plantilla tal cual, sin añadir "Adaptado", "Modificado" ni similares

"""

    user_prompt = f"Entreno actual:\n{workout_context}\n\n{rag_section}Instrucción: {instruction}"
    if state.get("athlete_context"):
        user_prompt = format_context_for_prompt(state["athlete_context"]) + "\n\n" + user_prompt
    logger.agent_input("WorkoutEditorAgent", user_prompt)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_completion_tokens=1500,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    changes = json.loads(response.choices[0].message.content)
    changes["status"] = changes.get("status", "modified")

    if "structure" in changes:
        changes["planned_duration_s"] = _calculate_duration(changes["structure"])
        # Calcular TSS estimado si hay FTP disponible
        ftp = (state.get("athlete_context") or {}).get("ftp")
        if ftp:
            tss = estimate_tss(changes["structure"], float(ftp))
            if tss is not None:
                changes["estimated_tss"] = tss

    changes = _sanitize_changes_for_db(changes)
    
    # Resolver nutrition: usa resolve_nutrition para manejar todos los casos
    # (LLM no incluyó, LLM incluyó formato simple, LLM incluyó formato completo)
    if changes.get("template_id") and state.get("rag_templates"):
        template_id = changes["template_id"]
        selected_template = next((t for t in state["rag_templates"] if t.get("id") == template_id), None)
        nutrition_template = selected_template.get("nutrition_template") if selected_template else None
        athlete_context = state.get("athlete_context") or {}

        resolved = resolve_nutrition(
            nutrition_from_llm=changes.get("nutrition"),
            nutrition_template=nutrition_template,
            athlete_context=athlete_context,
        )
        if resolved:
            changes["nutrition"] = resolved
            logger.agent_start("WorkoutEditorAgent.nutrition", {
                "template_id": template_id,
                "source": "llm_full" if changes.get("nutrition") and not nutrition_template else
                          "llm_converted" if changes.get("nutrition") else "template_converted",
            })

    logger.llm_call("WorkoutEditorAgent", response.usage.prompt_tokens, response.usage.completion_tokens, duration_ms)
    logger.agent_output("WorkoutEditorAgent", {k: v for k, v in changes.items() if k != "structure"})

    actions = list(state.get("actions_taken", []))

    if target_workout:
        workout_id = target_workout["id"]
        result = registry.execute("update_workout", {"workout_id": workout_id, "changes": changes})
    else:
        result = registry.execute("insert_workout", {
            "user_id": state["user_id"],
            "date": target_date,
            "fields": changes,
        })

    if result.success:
        actions.append(f"workout_modified:{target_date}")
        logger.agent_end("WorkoutEditorAgent", duration_ms, {
            "fields": list(changes.keys()),
            "duration_s": changes.get("planned_duration_s"),
            "op": "update" if target_workout else "insert",
            "date": target_date,
            "template_id": changes.get("template_id"),
        })
        return {
            **state,
            "new_workout": changes,
            "actions_taken": actions,
            "template_id": changes.get("template_id"),
        }
    else:
        logger.error("WorkoutEditorAgent", result.error or "unknown error")
        return {**state, "actions_taken": actions}


def _get_instruction(state: AgentState, agent_name: str) -> str | None:
    for step in state.get("operator_plan", []):
        if step.get("agent") == agent_name:
            return step.get("instruction")
    return None


def _extract_date(instruction: str) -> str | None:
    """Extrae una fecha YYYY-MM-DD de la instrucción del Operator si la contiene."""
    import re
    m = re.search(r'(\d{4}-\d{2}-\d{2})', instruction)
    return m.group(1) if m else None
