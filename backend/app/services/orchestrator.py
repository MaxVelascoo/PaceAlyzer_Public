import time
from uuid import uuid4
from agents.graph import agent_graph
from db.repositories import get_or_create_session, save_message, get_recent_messages
from utils.logger import logger, trace_id_var
from utils.request_metrics import start_request_metrics


def handle_message(user_id: str, message: str, date: str) -> dict:
    trace_id = str(uuid4())[:8]
    trace_id_var.set(trace_id)
    start_request_metrics(trace_id, user_id, date, message)

    t0 = time.monotonic()
    logger.graph_start(user_id, message, date)

    # 1. Obtener/crear sesión
    session_id = get_or_create_session(user_id)

    # 2. Guardar mensaje del usuario
    save_message(session_id, "user", message)

    # 3. Cargar historial reciente (excluye el mensaje que acabamos de guardar)
    history = get_recent_messages(session_id, limit=11)
    # Quitar el último (el que acabamos de insertar) para no duplicarlo
    conversation_history = history[:-1] if history else []

    initial_state = {
        "user_id": user_id,
        "message": message,
        "date": date,
        "session_id": session_id,
        "conversation_history": conversation_history,
    }

    try:
        final_state = agent_graph.invoke(initial_state)
    except Exception as e:
        logger.error("GRAPH", str(e), {"user_id": user_id[:8], "date": date})
        raise

    reply = final_state.get("reply", "No pude procesar tu mensaje.")
    action_taken = final_state.get("action_taken", "none")

    # Extraer fecha y título del entreno modificado para la preview
    workout_date = None
    workout_title = None
    if action_taken and action_taken.startswith("workout_modified"):
        for a in final_state.get("actions_taken", []):
            if a.startswith("workout_modified:"):
                workout_date = a.split(":", 1)[1]
                break
        new_workout = final_state.get("new_workout")
        if new_workout:
            workout_title = new_workout.get("title")

    # Extraer plan semanal si lo hay
    week_plan = None
    if action_taken == "week_plan_created":
        week_plan = final_state.get("week_plan_summary")  # [{date, title, duration_min}]

    # Construir metadata para persistir la preview
    metadata: dict | None = None
    if workout_date and workout_title:
        metadata = {"workout_preview": {"date": workout_date, "title": workout_title}}
    elif week_plan:
        total_min = sum(d.get("duration_min", 0) for d in week_plan)
        total_hours = round(total_min / 60 * 10) / 10
        metadata = {"week_plan_preview": {"days": week_plan, "total_hours": total_hours}}

    # 4. Guardar respuesta del asistente con metadata embebida
    save_message(session_id, "assistant", reply, metadata=metadata)

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.graph_end(duration_ms, action_taken)

    return {
        "reply": reply,
        "action_taken": action_taken,
        "workout_date": workout_date,
        "workout_title": workout_title,
        "week_plan": week_plan,
    }
