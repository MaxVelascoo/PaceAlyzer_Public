import json
import re
import time
from agents.state import AgentState
from llm.client import client, MODEL
from tools.registry import registry
from services.context_service import format_context_for_prompt
from utils.logger import logger


SYSTEM_PROMPT = """Eres un nutricionista deportivo especializado en ciclismo.
Recibirás información del entreno y una instrucción. Genera la nutrición completa para ese entreno.

FORMATO EXACTO DE RESPUESTA (JSON):
{
  "version": 1,
  "pre": {
    "window_min": {"min": 60, "max": 90},
    "targets": [
      {"key": "carbs", "label": "Carbohidratos", "unit": "g", "value": 60}
    ],
    "notes": ["Nota sobre la ingesta pre-entreno"],
    "examples": ["Ejemplo de comida 1", "Ejemplo de comida 2"]
  },
  "during": {
    "targets": [
      {"key": "carbs", "label": "Carbohidratos", "unit": "g/h", "value": 60}
    ],
    "notes": ["Nota sobre la ingesta durante el entreno"],
    "examples": ["Gel energético", "Bebida isotónica"]
  },
  "post": {
    "targets": [
      {"key": "carbs", "label": "Carbohidratos", "unit": "g", "value": 80},
      {"key": "protein", "label": "Proteínas", "unit": "g", "value": 20}
    ],
    "notes": ["Nota sobre la recuperación"],
    "examples": ["Batido de proteínas con plátano", "Pasta con pollo"]
  }
}

REGLAS:
- Adapta los valores según la intensidad y duración del entreno
- Para entrenos de alta intensidad (Z4-Z6): más carbohidratos, más proteína post
- Para entrenos de baja intensidad (Z1-Z2): menos carbohidratos
- Para entrenos cortos (<45min): el bloque "during" puede tener targets mínimos
- Devuelve SIEMPRE los tres bloques: pre, during, post
- Responde SOLO con el JSON, sin texto adicional"""


def run(state: AgentState) -> AgentState:
    """Nodo LangGraph: genera la nueva nutrición y la persiste via ToolRegistry."""
    instruction = _get_instruction(state, "nutrition_editor")
    if not instruction:
        logger.agent_skip("NutritionEditorAgent", "no instruction from Operator")
        return state

    # Extraer fecha de la instrucción (puede ser distinta a state["date"])
    target_date = _extract_date(instruction) or state["date"]

    logger.agent_start("NutritionEditorAgent", {
        "instruction": instruction[:60],
        "date": target_date,
    })
    t0 = time.monotonic()

    # Leer el entreno de la fecha objetivo para tener contexto
    plan_result = registry.execute("get_current_plan", {
        "user_id": state["user_id"],
        "date": target_date,
    })

    workout_id = None
    workout_context = "No hay entreno definido para ese día."

    if plan_result.success and plan_result.data:
        w = plan_result.data
        workout_id = w.get("id")
        duration_min = (w.get("planned_duration_s") or 0) // 60
        structure = w.get("structure", {})
        session = structure.get("session", {})
        workout_context = (
            f"Título: {w.get('title')}\n"
            f"Duración: {duration_min} min\n"
            f"Objetivo: {session.get('goal', 'No especificado')}\n"
            f"Descripción: {session.get('description', '')}"
        )
    elif state.get("current_workout") and target_date == state["date"]:
        w = state["current_workout"]
        workout_id = w.get("id")
        duration_min = (w.get("planned_duration_s") or 0) // 60
        workout_context = f"Título: {w.get('title')}, Duración: {duration_min} min"

    if not workout_id:
        logger.error("NutritionEditorAgent", f"no workout found for date {target_date}")
        return state

    # Leer nutrición actual si existe
    nutrition_result = registry.execute("get_nutrition", {
        "user_id": state["user_id"],
        "date": target_date,
    })
    current_nutrition = "No hay nutrición definida actualmente."
    if nutrition_result.success:
        current_nutrition = json.dumps(nutrition_result.data.get("nutrition"), ensure_ascii=False, indent=2)

    user_prompt = (
        f"Entreno:\n{workout_context}\n\n"
        f"Nutrición actual:\n{current_nutrition}\n\n"
        f"Instrucción: {instruction}"
    )
    if state.get("athlete_context"):
        user_prompt = format_context_for_prompt(state["athlete_context"]) + "\n\n" + user_prompt
    logger.agent_input("NutritionEditorAgent", user_prompt)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_completion_tokens=800,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    new_nutrition = json.loads(response.choices[0].message.content)

    logger.llm_call("NutritionEditorAgent", response.usage.prompt_tokens, response.usage.completion_tokens, duration_ms)
    logger.agent_output("NutritionEditorAgent", new_nutrition)

    result = registry.execute("update_nutrition", {
        "workout_id": workout_id,
        "nutrition": new_nutrition,
    })

    actions = list(state.get("actions_taken", []))
    if result.success:
        actions.append(f"nutrition_modified:{target_date}")
        logger.agent_end("NutritionEditorAgent", duration_ms, {
            "sections": list(new_nutrition.keys()),
            "date": target_date,
        })
        return {**state, "new_nutrition": new_nutrition, "actions_taken": actions}
    else:
        logger.error("NutritionEditorAgent", result.error or "unknown error")
        return {**state, "actions_taken": actions}


def _get_instruction(state: AgentState, agent_name: str) -> str | None:
    for step in state.get("operator_plan", []):
        if step.get("agent") == agent_name:
            return step.get("instruction")
    return None


def _extract_date(instruction: str) -> str | None:
    m = re.search(r'(\d{4}-\d{2}-\d{2})', instruction)
    return m.group(1) if m else None
