from langgraph.graph import StateGraph, END
import time
from agents.state import AgentState
from agents import (
    operator_agent,
    library_agent,
    workout_editor_agent,
    nutrition_editor_agent,
    week_planner_agent,
    explainer_agent,
)
from tools.registry import registry
from services.context_service import get_athlete_context
from utils.logger import logger


def _load_context(state: AgentState) -> AgentState:
    """Nodo inicial: lee el entreno del día y el contexto completo del atleta."""
    t0 = time.monotonic()
    result = registry.execute("get_current_plan", {
        "user_id": state["user_id"],
        "date": state["date"],
    })
    current_workout = result.data if result.success else None

    try:
        athlete_context = get_athlete_context(state["user_id"], state["date"])
    except Exception as e:
        logger.error("load_context", f"Error cargando athlete_context: {e}", non_blocking=True)
        athlete_context = None

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.agent_end("load_context", duration_ms, {
        "workout": current_workout.get("title", "?")[:30] if current_workout else "none",
        "has_context": athlete_context is not None,
    })
    return {**state, "current_workout": current_workout, "athlete_context": athlete_context}


def _route_after_operator(state: AgentState) -> str:
    plan = state.get("operator_plan", [])
    agent_names = [step.get("agent") for step in plan]
    logger.agent_start("router", {"plan": agent_names})
    if "week_planner" in agent_names:
        return "week_planner"
    if "librarian" in agent_names:
        return "librarian"
    if "workout_editor" in agent_names:
        return "workout_editor"
    if "nutrition_editor" in agent_names:
        return "nutrition_editor"
    return "explainer"


def _route_after_librarian(state: AgentState) -> str:
    """Después del RAG, va al workout_editor (o week_planner si está en el plan)."""
    plan = state.get("operator_plan", [])
    agent_names = [step.get("agent") for step in plan]
    if "week_planner" in agent_names:
        return "week_planner"
    return "workout_editor"


def _route_after_workout_editor(state: AgentState) -> str:
    """Después de editar el entreno, ¿hay que editar nutrición también?"""
    plan = state.get("operator_plan", [])
    agent_names = [step.get("agent") for step in plan]
    if "nutrition_editor" in agent_names:
        return "nutrition_editor"
    return "explainer"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Nodos
    graph.add_node("load_context", _load_context)
    graph.add_node("operator", operator_agent.run)
    graph.add_node("librarian", library_agent.run)
    graph.add_node("workout_editor", workout_editor_agent.run)
    graph.add_node("nutrition_editor", nutrition_editor_agent.run)
    graph.add_node("week_planner", week_planner_agent.run)
    graph.add_node("explainer", explainer_agent.run)

    # Flujo principal
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "operator")

    # Operator decide el primer agente
    graph.add_conditional_edges(
        "operator",
        _route_after_operator,
        {
            "librarian": "librarian",
            "workout_editor": "workout_editor",
            "nutrition_editor": "nutrition_editor",
            "week_planner": "week_planner",
            "explainer": "explainer",
        },
    )

    # Después de librarian, va al workout_editor o week_planner
    graph.add_conditional_edges(
        "librarian",
        _route_after_librarian,
        {
            "workout_editor": "workout_editor",
            "week_planner": "week_planner",
        },
    )

    # Después de workout_editor, puede ir a nutrition_editor o al explainer
    graph.add_conditional_edges(
        "workout_editor",
        _route_after_workout_editor,
        {
            "nutrition_editor": "nutrition_editor",
            "explainer": "explainer",
        },
    )

    # Todos convergen en el explainer
    graph.add_edge("nutrition_editor", "explainer")
    graph.add_edge("week_planner", "explainer")
    graph.add_edge("explainer", END)

    return graph.compile()


# Instancia global del grafo compilado
agent_graph = build_graph()
