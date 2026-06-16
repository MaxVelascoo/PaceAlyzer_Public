import time
from agents.state import AgentState
from llm.client import client, MODEL
from utils.logger import logger


SYSTEM_PROMPT = """Eres Pazey, el asistente de entrenamiento ciclista.
Redacta una respuesta breve y natural confirmando lo que se ha hecho.

REGLAS:
- Máximo 2-3 frases cortas
- Sé directo, no uses frases como "He actualizado tu entrenamiento con un nuevo título, descripción y detalles"
- Menciona qué tipo de entreno es y la fecha si es relevante
- Tono cercano, como un entrenador personal
- Sin emojis
- Si se creó un entreno nuevo desde la biblioteca, menciona que lo has seleccionado y adaptado de la biblioteca
- Si se generó desde cero (sin plantilla), di que lo has creado
- Si se modificó uno existente, di qué cambió concretamente
- Si se generó un plan semanal, menciona cuántos días y el rango de fechas de forma natural
- Si no se hizo nada, explícalo con una frase"""


def run(state: AgentState) -> AgentState:
    """Nodo LangGraph: genera la respuesta final que verá el usuario en el chat."""
    logger.agent_start("ExplainerAgent", {"actions": state.get("actions_taken", [])})
    t0 = time.monotonic()

    actions = state.get("actions_taken", [])
    actions_summary = ", ".join(actions) if actions else "ninguna acción ejecutada"
    date_fmt = _fmt(state.get("date", ""))

    context_parts = [f"Petición del usuario: \"{state['message']}\""]
    context_parts.append(f"Fecha: {date_fmt}")
    context_parts.append(f"Acciones: {actions_summary}")

    if state.get("new_workout"):
        w = state["new_workout"]
        duration_min = w.get('planned_duration_s', 0) // 60
        context_parts.append(f"Entreno: '{w.get('title', '')}', duración real: {duration_min} min")
        if w.get("structure", {}).get("session", {}).get("goal"):
            context_parts.append(f"Objetivo: {w['structure']['session']['goal']}")
        # Indicar si se usó una plantilla de la biblioteca
        if state.get("template_id"):
            context_parts.append("Origen: adaptado de plantilla de la biblioteca de entrenos")
    if state.get("new_nutrition"):
        context_parts.append("Nutrición actualizada.")
    if state.get("week_plan_summary"):
        lines = [f"  - {d['date']}: {d['title']} ({d['duration_min']}min)" for d in state["week_plan_summary"]]
        context_parts.append("Plan semanal generado:\n" + "\n".join(lines))

    explainer_input = "\n".join(context_parts)
    logger.agent_input("ExplainerAgent", explainer_input)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": explainer_input},
        ],
        temperature=0.5,
        max_completion_tokens=150,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    reply = response.choices[0].message.content.strip()

    logger.llm_call("ExplainerAgent", response.usage.prompt_tokens, response.usage.completion_tokens, duration_ms)
    logger.agent_output("ExplainerAgent", reply)
    logger.agent_end("ExplainerAgent", duration_ms, {"reply": reply[:80]})

    action_taken = "none"
    if any("workout_modified" in a for a in actions):
        action_taken = "workout_modified"
    elif any("workout_cancelled" in a or "skipped" in a for a in actions):
        action_taken = "workout_cancelled"
    elif any("nutrition_modified" in a for a in actions):
        action_taken = "nutrition_modified"
    elif any("week_plan_saved" in a for a in actions):
        action_taken = "week_plan_created"

    return {**state, "reply": reply, "action_taken": action_taken}


def _fmt(iso_date: str) -> str:
    try:
        y, m, d = iso_date.split("-")
        return f"{d}-{m}-{y}"
    except Exception:
        return iso_date
