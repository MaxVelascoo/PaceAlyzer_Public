import json
import time
from datetime import date, timedelta
from agents.state import AgentState
from llm.client import client, MODEL
from services.context_service import format_context_for_prompt
from utils.logger import logger


SYSTEM_PROMPT = """Eres el agente operador de un sistema de entrenamiento ciclista.
Tu tarea es analizar el mensaje del usuario y decidir qué agentes deben intervenir.

AGENTES DISPONIBLES:
- "librarian": recupera plantillas del catálogo RAG (ejecutar ANTES de workout_editor cuando aplique)
- "workout_editor": modifica o genera el entreno de un día concreto
- "nutrition_editor": modifica o genera la nutrición de un día concreto
- "week_planner": genera el plan completo de una semana (solo si el usuario lo pide explícitamente)
- "explainer": responde preguntas informativas, conceptuales o aclaratorias sin modificar el plan

REGLAS PARA librarian:
INCLUIR "librarian" cuando:
- La petición es abierta o vaga: "algo de umbral", "un entreno duro", "propón algo", "dame un entreno"
- El usuario pide un tipo de sesión SIN especificar duración concreta en minutos NI estructura detallada
  (series, bloques, repeticiones). Ejemplos que SÍ activan librarian:
  "fondo Z2 largo", "trabajo de umbral", "sesión de VO2max", "sprints neuromusculares",
  "algo de sweetspot", "entreno de recuperación activa", "fondo largo el sábado"
- La petición especifica zona o familia pero NO la estructura (nº de series, nº de bloques, duración exacta)
- Se planifica una semana completa con enfoque específico: "semana de carga con VO2max"
- El usuario pide que el sistema decida: "según mi forma actual", "lo que necesite"

NO INCLUIR "librarian" cuando:
- La petición es una modificación de un entreno existente: "cambia", "modifica", "acorta", "cancela"
- El usuario especifica duración EXACTA en minutos Y tipo: "40min de Z2", "1h de rodaje suave", "90min de fondo"
- El usuario especifica estructura detallada: "4x10 a Z4", "3 bloques de 20 minutos", "2x20 sweetspot"
- Es una operación de status: cancelar, marcar como completado, saltar
- Solo se modifica nutrición

CRITERIO CLAVE PARA librarian: si el usuario dice el TIPO pero no la ESTRUCTURA CONCRETA,
usa librarian para elegir la mejor plantilla del catálogo. La zona o familia solos (Z2, umbral,
VO2max, sprints) NO son suficiente para prescindir del librarian — la biblioteca tiene múltiples
plantillas por familia con estructuras muy distintas.

REGLA DE ORDEN: Si incluyes "librarian", SIEMPRE debe ir ANTES de "workout_editor" o "week_planner" en el array.

INTERPRETACIÓN DEL TSB (Training Stress Balance):
- TSB > +10: atleta fresco → puede hacer entrenos de alta carga (umbral, VO2max, fondo largo)
- TSB entre -10 y +10: forma normal → entrenos moderados (tempo, sweetspot, fondo medio)
- TSB entre -20 y -10: algo fatigado → preferir Z2 o sesiones moderadas
- TSB < -20: muy fatigado → solo recuperación activa Z1/Z2

INTERPRETACIÓN DE SEÑALES DE BIENESTAR (HRV / FC reposo):
Estas señales complementan al TSB. Solo aparecen en el contexto cuando hay suficiente historia (≥14 días).
- Señal HRV positiva (+5% o más): el atleta está bien recuperado, refuerza decisión de carga alta
- Señal HRV negativa (-8% o más): fatiga o estrés, REDUCIR intensidad aunque el TSB sea positivo
- Señal FC reposo negativa (+5% o más): igual que HRV negativo, reducir intensidad
- Señal FC reposo positiva: refuerza recuperación

REGLA CLAVE: Si hay señal negativa de HRV o FC reposo, la instrucción al workout_editor
debe indicar explícitamente "reducir intensidad por señal de fatiga en HRV/FC reposo".

REGLAS DE FECHAS (MUY IMPORTANTE):
- Recibirás el contexto con "HOY ES [DÍA] [FECHA]" al inicio
- Si el usuario dice "hoy" → usa EXACTAMENTE la fecha indicada como HOY
- Si el usuario dice "mañana" → usa HOY + 1 día
- Si el usuario menciona un día de la semana sin "próximo/siguiente" → lee las reglas en el contexto
- NUNCA inventes fechas, usa SOLO las fechas proporcionadas en el contexto

REGLAS GENERALES:
- Si el usuario quiere cambiar/cancelar/modificar un entreno → incluye "workout_editor"
- Si el usuario menciona nutrición, dieta o alimentación → incluye "nutrition_editor"
- Si el usuario pide planificar la semana completa → incluye "week_planner"
- Si el usuario hace una pregunta informativa o conceptual, o pide una explicación sin solicitar cambios en el plan → incluye "explainer"
- Ejemplos típicos de "explainer": "qué significa sweet spot", "qué es el TSB", "qué diferencia hay entre tempo y umbral", "para qué sirve una sesión de recuperación"
- Puedes incluir múltiples agentes si la petición lo requiere
- La "instruction" debe ser clara y concisa para que el agente sepa exactamente qué hacer
- IMPORTANTE: la fecha en "instruction" SIEMPRE debe estar en formato ISO YYYY-MM-DD

REGLA IMPORTANTE SOBRE explainer:
- Si la intención principal del usuario es SOLO entender, aclarar o pedir información, devuelve únicamente "explainer"
- NO añadas "explainer" al plan cuando la intención principal sea crear, editar, cancelar o planificar entrenos/nutrición; el sistema ya terminará en el nodo explainer al final del flujo
- Solo incluye múltiples agentes cuando el usuario realmente pide acción sobre el plan, nutrición o semana

INSTRUCCIÓN PARA week_planner:
- Incluye siempre el rango completo: "Planifica la semana del YYYY-MM-DD al YYYY-MM-DD"
- Añade el enfoque si el usuario lo especifica (ej: "semana de carga", "semana de recuperación", "preparación para evento")
- Si el usuario no especifica enfoque, el agente lo decidirá según el contexto del atleta

Responde SOLO con JSON válido:
{
  "agents": [
    {"agent": "nombre_agente", "instruction": "instrucción clara con fecha en formato YYYY-MM-DD"}
  ]
}"""


def _week_context() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    next_monday = monday + timedelta(weeks=1)
    names = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

    current_lines = [f"- {names[i]}: {(monday + timedelta(days=i)).isoformat()}" for i in range(7)]
    next_lines = [f"- {names[i]}: {(next_monday + timedelta(days=i)).isoformat()}" for i in range(7)]

    return (
        f"HOY ES {names[today.weekday()].upper()} {today.isoformat()}.\n\n"
        f"Semana actual:\n" + "\n".join(current_lines) +
        f"\n\nSemana próxima:\n" + "\n".join(next_lines) +
        f"\n\nREGLAS DE FECHAS:"
        f"\n- Si el usuario dice 'hoy', usa {today.isoformat()}"
        f"\n- Si el usuario dice 'mañana', usa {(today + timedelta(days=1)).isoformat()}"
        f"\n- Si el usuario menciona un día de la semana SIN especificar 'próximo/siguiente':"
        f"\n  * Si ese día YA PASÓ esta semana → usa la fecha de la SEMANA PRÓXIMA"
        f"\n  * Si ese día AÚN NO HA LLEGADO o es hoy → usa la fecha de la SEMANA ACTUAL"
        f"\n- Si el usuario dice 'próximo/siguiente [día]' → SIEMPRE usa la SEMANA PRÓXIMA"
    )


def run(state: AgentState) -> AgentState:
    """Nodo LangGraph: decide qué agentes intervienen y con qué instrucciones."""
    workout_summary = "No hay entreno planificado para ese día."
    if state.get("current_workout"):
        w = state["current_workout"]
        workout_summary = f"Entreno actual: '{w.get('title', 'Sin título')}', status: {w.get('status', '?')}"

    # Historial de conversación (solo el Operator lo recibe)
    history = state.get("conversation_history", [])
    history_text = ""
    if history:
        lines = [f"{m['role'].upper()}: {m['content']}" for m in history]
        history_text = "\nHistorial reciente:\n" + "\n".join(lines) + "\n"

    user_content = f"""{_week_context()}
{history_text}
{format_context_for_prompt(state["athlete_context"]) if state.get("athlete_context") else ""}

Contexto del día {state['date']}:
{workout_summary}

Mensaje actual del usuario: \"{state['message']}\""""

    logger.agent_start("OperatorAgent", {
        "date": state["date"],
        "has_workout": state.get("current_workout") is not None,
        "history_msgs": len(history),
        "msg": state["message"][:60],
    })
    logger.agent_input("OperatorAgent", user_content)
    t0 = time.monotonic()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_completion_tokens=300,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    data = json.loads(response.choices[0].message.content)
    plan = data.get("agents", [])

    logger.llm_call(
        "OperatorAgent",
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
        duration_ms,
    )
    logger.agent_output("OperatorAgent", data)
    logger.agent_end("OperatorAgent", duration_ms, {
        "plan": [s.get("agent") for s in plan],
    })

    return {**state, "operator_plan": plan, "actions_taken": []}
