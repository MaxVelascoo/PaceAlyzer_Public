"""
Servicio para analizar workouts y extraer metadatos estructurados.
Estos metadatos enriquecen los embeddings para mejorar la búsqueda semántica.
"""

from typing import Dict, List, Optional


def analyze_workout_structure(template: dict) -> dict:
    """
    Analiza la estructura de un workout y extrae metadatos semánticos.
    
    Returns:
        dict con campos:
        - session_family: str (recovery, endurance, tempo, sweetspot, threshold, vo2max, anaerobic, neuromuscular, mixed)
        - dominant_zone: str (Z1-Z7)
        - structure_type: str (long_intervals, short_intervals, microbursts, steady, sprints, pyramids, mixed)
        - primary_goal: str (endurance, power, speed, recovery, technique)
        - fatigue_suitability: str (fresh, normal, fatigued, very_fatigued)
        - duration_band: str (short, medium, long, very_long)
        - tss_band: str (very_low, low, moderate, high, very_high)
    """
    structure = template.get("structure", {})
    steps = structure.get("steps", [])
    intensity_level = template.get("intensity_level", "moderate")
    duration_min = template.get("duration_min", 60)
    est_tss = template.get("est_tss", 50)
    title = template.get("title", "").lower()
    description = template.get("description", "").lower()
    tags = template.get("tags", [])
    
    # Analizar zonas dominantes
    zone_time = _calculate_zone_time(steps)
    dominant_zone = _get_dominant_zone(zone_time)
    
    # Determinar familia de sesión
    session_family = _determine_session_family(
        dominant_zone, intensity_level, title, description, tags
    )
    
    # Determinar tipo de estructura
    structure_type = _determine_structure_type(steps, title, description)
    
    # Determinar objetivo principal
    primary_goal = _determine_primary_goal(session_family, structure_type, title, description)
    
    # Determinar idoneidad según fatiga
    fatigue_suitability = _determine_fatigue_suitability(session_family, intensity_level, est_tss)
    
    # Bandas de duración
    duration_band = _get_duration_band(duration_min)
    
    # Bandas de TSS
    tss_band = _get_tss_band(est_tss)
    
    return {
        "session_family": session_family,
        "dominant_zone": dominant_zone,
        "structure_type": structure_type,
        "primary_goal": primary_goal,
        "fatigue_suitability": fatigue_suitability,
        "duration_band": duration_band,
        "tss_band": tss_band,
    }


def _calculate_zone_time(steps: List[dict]) -> Dict[str, int]:
    """Calcula tiempo en segundos por zona."""
    zone_time = {f"Z{i}": 0 for i in range(1, 8)}
    
    def walk(steps_list: List[dict], multiplier: int = 1):
        for step in steps_list:
            if step.get("type") == "interval":
                duration = step.get("duration_s", 0)
                target = step.get("target", {})
                zone = target.get("zone", "Z2")
                if zone in zone_time:
                    zone_time[zone] += duration * multiplier
            elif step.get("type") == "repeat":
                repeat = step.get("repeat", 1)
                walk(step.get("steps", []), multiplier * repeat)
    
    walk(steps)
    return zone_time


def _get_dominant_zone(zone_time: Dict[str, int]) -> str:
    """Retorna la zona con más tiempo."""
    if not zone_time or sum(zone_time.values()) == 0:
        return "Z2"
    return max(zone_time.items(), key=lambda x: x[1])[0]


def _determine_session_family(
    dominant_zone: str,
    intensity_level: str,
    title: str,
    description: str,
    tags: List[str]
) -> str:
    """Determina la familia de sesión basándose en múltiples señales."""
    text = f"{title} {description} {' '.join(tags)}".lower()
    
    # Palabras clave por familia
    keywords = {
        "recovery": ["recuperación", "recovery", "activa", "z1", "suave", "descanso"],
        "endurance": ["endurance", "fondo", "base", "aeróbico", "z2", "largo"],
        "tempo": ["tempo", "z3", "ritmo", "sostenido"],
        "sweetspot": ["sweetspot", "sweet spot", "ss", "z3-z4"],
        "threshold": ["umbral", "threshold", "z4", "ftp", "lactato"],
        "vo2max": ["vo2max", "vo2", "z5", "aeróbico máximo", "capacidad"],
        "anaerobic": ["anaeróbico", "anaerobic", "z6", "lactato", "resistencia"],
        "neuromuscular": ["neuromuscular", "z7", "sprint", "explosivo", "potencia máxima"],
    }
    
    # Contar coincidencias
    scores = {}
    for family, words in keywords.items():
        scores[family] = sum(1 for word in words if word in text)
    
    # Si hay coincidencias claras, usar eso
    max_score = max(scores.values())
    if max_score > 0:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    # Fallback: usar zona dominante
    zone_to_family = {
        "Z1": "recovery",
        "Z2": "endurance",
        "Z3": "tempo",
        "Z4": "threshold",
        "Z5": "vo2max",
        "Z6": "anaerobic",
        "Z7": "neuromuscular",
    }
    
    return zone_to_family.get(dominant_zone, "endurance")


def _determine_structure_type(steps: List[dict], title: str, description: str) -> str:
    """Determina el tipo de estructura del workout."""
    text = f"{title} {description}".lower()
    
    # Contar intervalos y su duración
    intervals = []
    
    def walk(steps_list: List[dict]):
        for step in steps_list:
            if step.get("type") == "interval":
                duration = step.get("duration_s", 0)
                target = step.get("target", {})
                zone = target.get("zone", "Z2")
                # Solo contar intervalos de alta intensidad (Z4+)
                if zone in ["Z4", "Z5", "Z6", "Z7"] and duration > 0:
                    intervals.append(duration)
            elif step.get("type") == "repeat":
                walk(step.get("steps", []))
    
    walk(steps)
    
    # Palabras clave
    if any(word in text for word in ["sprint", "explosivo", "neuromuscular"]):
        return "sprints"
    
    if any(word in text for word in ["microburst", "micro", "30\""]):
        return "microbursts"
    
    if any(word in text for word in ["pirámide", "pyramid", "progresivo", "evolutivo"]):
        return "pyramids"
    
    # Analizar intervalos
    if not intervals:
        return "steady"
    
    avg_interval = sum(intervals) / len(intervals) if intervals else 0
    
    if avg_interval < 60:  # < 1 min
        return "microbursts"
    elif avg_interval < 180:  # 1-3 min
        return "short_intervals"
    elif avg_interval >= 180:  # >= 3 min
        return "long_intervals"
    
    return "mixed"


def _determine_primary_goal(session_family: str, structure_type: str, title: str, description: str) -> str:
    """Determina el objetivo principal del workout."""
    text = f"{title} {description}".lower()
    
    # Mapeo directo por familia
    family_to_goal = {
        "recovery": "recovery",
        "endurance": "endurance",
        "tempo": "endurance",
        "sweetspot": "power",
        "threshold": "power",
        "vo2max": "power",
        "anaerobic": "power",
        "neuromuscular": "speed",
    }
    
    # Palabras clave específicas
    if any(word in text for word in ["técnica", "cadencia", "pedaling"]):
        return "technique"
    
    if any(word in text for word in ["velocidad", "speed", "sprint"]):
        return "speed"
    
    return family_to_goal.get(session_family, "endurance")


def _determine_fatigue_suitability(session_family: str, intensity_level: str, est_tss: float) -> str:
    """Determina para qué nivel de fatiga es apropiado el workout."""
    
    # Recovery siempre es para fatigados
    if session_family == "recovery":
        return "very_fatigued"
    
    # Endurance/tempo son versátiles
    if session_family in ["endurance", "tempo"]:
        if est_tss < 60:
            return "fatigued"
        elif est_tss < 90:
            return "normal"
        else:
            return "fresh"
    
    # Sweetspot/threshold requieren estar relativamente frescos
    if session_family in ["sweetspot", "threshold"]:
        if est_tss < 80:
            return "normal"
        else:
            return "fresh"
    
    # VO2max/anaerobic/neuromuscular requieren estar frescos
    if session_family in ["vo2max", "anaerobic", "neuromuscular"]:
        return "fresh"
    
    # Fallback por intensidad
    intensity_to_fatigue = {
        "easy": "very_fatigued",
        "moderate": "fatigued",
        "hard": "normal",
        "very_hard": "fresh",
    }
    
    return intensity_to_fatigue.get(intensity_level, "normal")


def _get_duration_band(duration_min: int) -> str:
    """Clasifica la duración en bandas."""
    if duration_min < 60:
        return "short"
    elif duration_min < 90:
        return "medium"
    elif duration_min < 150:
        return "long"
    else:
        return "very_long"


def _get_tss_band(est_tss: float) -> str:
    """Clasifica el TSS en bandas."""
    if est_tss < 40:
        return "very_low"
    elif est_tss < 70:
        return "low"
    elif est_tss < 100:
        return "moderate"
    elif est_tss < 150:
        return "high"
    else:
        return "very_high"


def build_enriched_embedding_text(template: dict) -> str:
    """
    Construye el texto para embedding.
    
    Si la plantilla tiene embedding_text ya generado (campo de BD),
    lo usa directamente — es el texto canónico con el nuevo formato
    SUMMARY + RELATED_CONCEPTS + SEMANTIC_LABELS.
    
    Si no existe embedding_text, cae al método programático legacy
    para mantener compatibilidad hacia atrás.
    """
    # Usar embedding_text canónico si está disponible
    if template.get("embedding_text"):
        return template["embedding_text"]

    # ── Fallback legacy (programático) ───────────────────────────────────────
    parts = []

    title = template.get("title", "")
    if title:
        parts.append(title)

    description = template.get("description", "")
    if description:
        desc_short = description[:150].strip()
        if len(description) > 150:
            desc_short += "..."
        parts.append(desc_short)

    tags = template.get("tags", [])
    if tags:
        parts.append(" ".join(tags[:5]))

    metadata = analyze_workout_structure(template)

    meta_parts = [
        f"familia:{metadata['session_family']}",
        f"zona:{metadata['dominant_zone']}",
        f"estructura:{metadata['structure_type']}",
        f"objetivo:{metadata['primary_goal']}",
        f"fatiga:{metadata['fatigue_suitability']}",
    ]
    parts.append(" ".join(meta_parts))

    duration_min = template.get("duration_min", 0)
    est_tss = template.get("est_tss", 0)
    if duration_min and est_tss:
        parts.append(f"{duration_min}min {int(est_tss)}TSS")

    return " | ".join(p for p in parts if p)
