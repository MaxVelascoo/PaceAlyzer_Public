"""
Utilidades compartidas para el manejo de plantillas nutricionales.

Centraliza la lógica de conversión entre el formato simple de workout_library
y el formato completo esperado por el frontend en planned_workouts.

Usado por: workout_editor_agent, week_planner_agent
"""


def is_simple_nutrition_format(nutrition: dict) -> bool:
    """
    Detecta si un objeto nutrition está en formato simple (workout_library)
    o en formato completo (planned_workouts / frontend).

    Formato simple:  {"pre": {"carbs_g_per_kg": 2.0, ...}}
    Formato completo: {"version": 1, "pre": {"targets": [...], ...}}
    """
    if not nutrition or not isinstance(nutrition, dict):
        return False

    # Indicador inequívoco de formato completo
    if "version" in nutrition:
        return False

    # Si algún bloque tiene "targets", es formato completo
    for block_key in ("pre", "during", "post"):
        block = nutrition.get(block_key)
        if isinstance(block, dict) and "targets" in block:
            return False

    # Si algún bloque tiene claves del formato simple, es formato simple
    simple_keys = {"carbs_g_per_kg", "protein_g_per_kg", "carbs_g_per_hour", "sodium_mg_per_hour"}
    for block_key in ("pre", "during", "post"):
        block = nutrition.get(block_key)
        if isinstance(block, dict) and simple_keys & block.keys():
            return True

    return False


def convert_nutrition_to_full(nutrition_template: dict, athlete_context: dict) -> dict:
    """
    Convierte el formato simple de nutrition_template (workout_library)
    al formato completo esperado por el frontend (planned_workouts).

    Formato simple (workout_library):
        {
          "pre":    {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
          "during": {"carbs_g_per_hour": 80.0, "sodium_mg_per_hour": 500.0},
          "post":   {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4}
        }

    Formato completo (planned_workouts):
        {
          "version": 1,
          "pre": {
            "targets": [
              {"key": "carbs",   "label": "Carbohidratos", "unit": "g",   "value": 156},
              {"key": "protein", "label": "Proteínas",     "unit": "g",   "value": 16}
            ],
            "window_min": {"min": 60, "max": 90},
            "notes":    ["Consumir 60-90 minutos antes del entreno"],
            "examples": ["Avena con plátano", "Tostadas con mermelada", "Batido de frutas"]
          },
          "during": { ... },
          "post":   { ... }
        }

    Los valores relativos (g/kg) se multiplican por el peso del atleta.
    Los valores por hora (g/h, mg/h) se pasan directamente.
    """
    weight_kg: float = float(
        athlete_context.get("weight") or athlete_context.get("weight_kg") or 75
    )

    result: dict = {"version": 1}

    # ── PRE ──────────────────────────────────────────────────────────────────
    pre = nutrition_template.get("pre", {})
    if pre:
        targets = []
        if "carbs_g_per_kg" in pre:
            targets.append({
                "key": "carbs",
                "label": "Carbohidratos",
                "unit": "g",
                "value": int(pre["carbs_g_per_kg"] * weight_kg),
            })
        if "protein_g_per_kg" in pre:
            targets.append({
                "key": "protein",
                "label": "Proteínas",
                "unit": "g",
                "value": int(pre["protein_g_per_kg"] * weight_kg),
            })
        result["pre"] = {
            "window_min": {"min": 60, "max": 90},
            "targets": targets,
            "notes": ["Consumir 60-90 minutos antes del entreno"],
            "examples": ["Avena con plátano", "Tostadas con mermelada", "Batido de frutas"],
        }

    # ── DURING ───────────────────────────────────────────────────────────────
    during = nutrition_template.get("during", {})
    if during:
        targets = []
        if "carbs_g_per_hour" in during:
            targets.append({
                "key": "carbs",
                "label": "Carbohidratos",
                "unit": "g/h",
                "value": int(during["carbs_g_per_hour"]),
            })
        if "sodium_mg_per_hour" in during:
            targets.append({
                "key": "sodium",
                "label": "Sodio",
                "unit": "mg/h",
                "value": int(during["sodium_mg_per_hour"]),
            })
        result["during"] = {
            "targets": targets,
            "notes": ["Consumir de forma regular durante el entreno"],
            "examples": ["Geles energéticos", "Bebida isotónica", "Barritas energéticas"],
        }

    # ── POST ─────────────────────────────────────────────────────────────────
    post = nutrition_template.get("post", {})
    if post:
        targets = []
        if "carbs_g_per_kg" in post:
            targets.append({
                "key": "carbs",
                "label": "Carbohidratos",
                "unit": "g",
                "value": int(post["carbs_g_per_kg"] * weight_kg),
            })
        if "protein_g_per_kg" in post:
            targets.append({
                "key": "protein",
                "label": "Proteínas",
                "unit": "g",
                "value": int(post["protein_g_per_kg"] * weight_kg),
            })
        result["post"] = {
            "targets": targets,
            "notes": ["Consumir dentro de los 30-60 minutos posteriores al entreno"],
            "examples": ["Batido de proteínas con plátano", "Pasta con pollo", "Arroz con atún"],
        }

    return result


def resolve_nutrition(
    nutrition_from_llm: dict | None,
    nutrition_template: dict | None,
    athlete_context: dict,
) -> dict | None:
    """
    Función de alto nivel que resuelve el campo nutrition final para un workout.

    Lógica:
      1. Si el LLM devolvió nutrition en formato completo → usarlo tal cual
      2. Si el LLM devolvió nutrition en formato simple → convertir
      3. Si el LLM no devolvió nutrition pero hay nutrition_template → convertir
      4. Si no hay nada → None

    Args:
        nutrition_from_llm:  Lo que devolvió el LLM (puede ser None, simple o completo)
        nutrition_template:  El nutrition_template de la plantilla RAG (formato simple)
        athlete_context:     Contexto del atleta (necesita "weight")

    Returns:
        dict en formato completo, o None si no hay datos.
    """
    # Caso 1 y 2: el LLM incluyó nutrition
    if nutrition_from_llm:
        if is_simple_nutrition_format(nutrition_from_llm):
            return convert_nutrition_to_full(nutrition_from_llm, athlete_context)
        return nutrition_from_llm  # ya está en formato completo

    # Caso 3: el LLM no incluyó nutrition pero hay plantilla
    if nutrition_template:
        return convert_nutrition_to_full(nutrition_template, athlete_context)

    # Caso 4: sin datos
    return None
