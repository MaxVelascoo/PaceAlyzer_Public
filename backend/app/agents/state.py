from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Input
    user_id: str
    message: str
    date: str

    # Sesión y memoria
    session_id: str
    conversation_history: list[dict]

    # Contexto leído de DB
    current_workout: dict | None
    athlete_context: dict | None

    # Plan del Operator
    operator_plan: list[dict]

    # Outputs de los agentes editores
    new_workout: dict | None
    new_nutrition: dict | None
    week_plan_summary: list[dict] | None  # [{date, title, duration_min}, ...]

    # Acciones ejecutadas
    actions_taken: list[str]

    # RAG context (workout library)
    rag_templates: list[dict] | None   # top-3 WorkoutTemplates del RAG, None si no se ejecutó
    template_id: str | None            # UUID de la plantilla usada como base (lo escribe workout_editor)

    # Respuesta final
    reply: str
    action_taken: str
