from db.repositories import get_planned_workout, update_planned_workout


def _fmt(iso_date: str) -> str:
    """Convierte YYYY-MM-DD a DD-MM-YYYY para mostrar al usuario."""
    try:
        y, m, d = iso_date.split("-")
        return f"{d}-{m}-{y}"
    except Exception:
        return iso_date


def modify_workout(user_id: str, date: str, changes: dict) -> tuple[bool, str]:
    workout = get_planned_workout(user_id, date)

    if not workout:
        return False, f"No hay entreno planificado para el {_fmt(date)}."

    update_planned_workout(workout["id"], changes)
    return True, f"Entreno del {_fmt(date)} actualizado correctamente."
