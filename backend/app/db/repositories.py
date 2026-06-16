from db.supabase_client import supabase


def get_planned_workout(user_id: str, date: str) -> dict | None:
    res = (
        supabase.table("planned_workouts")
        .select("*")
        .eq("user_id", user_id)
        .eq("date", date)
        .execute()
    )
    rows = res.data
    return rows[0] if rows else None


def update_planned_workout(workout_id: str, fields: dict) -> dict:
    import time as _time
    last_exc = None
    for attempt in range(3):
        try:
            res = (
                supabase.table("planned_workouts")
                .update(fields)
                .eq("id", workout_id)
                .execute()
            )
            return res.data
        except Exception as e:
            last_exc = e
            if attempt < 2:
                _time.sleep(1.5 ** attempt)
    raise last_exc


def insert_planned_workout(user_id: str, date: str, fields: dict) -> dict:
    payload = {
        "user_id": user_id,
        "date": date,
        "source": "user_modified",
        **fields,
    }
    # Retry hasta 3 veces por errores de red transitorios (SSL, timeout, etc.)
    import time as _time
    last_exc = None
    for attempt in range(3):
        try:
            res = (
                supabase.table("planned_workouts")
                .insert(payload)
                .execute()
            )
            return res.data[0] if res.data else {}
        except Exception as e:
            last_exc = e
            if attempt < 2:
                _time.sleep(1.5 ** attempt)
    raise last_exc


def get_week_planned_workouts(user_id: str, week_start: str, week_end: str) -> list[dict]:
    """Devuelve todos los entrenos planificados de una semana."""
    res = (
        supabase.table("planned_workouts")
        .select("id, date, title, status, planned_duration_s, planned_distance_m")
        .eq("user_id", user_id)
        .gte("date", week_start)
        .lte("date", week_end)
        .order("date", desc=False)
        .execute()
    )
    return res.data or []


def get_blocked_days(user_id: str, week_start: str, week_end: str) -> list[dict]:
    """Devuelve los días bloqueados de un rango de fechas."""
    res = (
        supabase.table("blocked_days")
        .select("date, reason")
        .eq("user_id", user_id)
        .gte("date", week_start)
        .lte("date", week_end)
        .execute()
    )
    return res.data or []


def delete_planned_workout(workout_id: str, user_id: str) -> bool:
    """Borra un entreno planificado. Verifica que pertenece al usuario."""
    res = (
        supabase.table("planned_workouts")
        .delete()
        .eq("id", workout_id)
        .eq("user_id", user_id)
        .execute()
    )
    return True


# ── Chat sessions ─────────────────────────────────────────────────────────────

def get_or_create_session(user_id: str) -> str:
    """
    Devuelve el session_id activo del usuario.
    Crea una nueva sesión si no existe ninguna o si la última tiene más de 24h.
    """
    from datetime import datetime, timezone, timedelta

    res = (
        supabase.table("chat_sessions")
        .select("id, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if res.data:
        session = res.data[0]
        created_at = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - created_at
        if age < timedelta(hours=24):
            return session["id"]

    # Crear nueva sesión
    new = (
        supabase.table("chat_sessions")
        .insert({"user_id": user_id})
        .execute()
    )
    return new.data[0]["id"]


def save_message(session_id: str, role: str, content: str, metadata: dict | None = None) -> None:
    """Guarda un mensaje. Si hay metadata, la embebe como JSON al final del content."""
    import json as _json
    stored_content = content
    if metadata:
        stored_content = content + "||META||" + _json.dumps(metadata, ensure_ascii=False)
    supabase.table("chat_messages").insert({
        "session_id": session_id,
        "role": role,
        "content": stored_content,
    }).execute()


def get_recent_messages(session_id: str, limit: int = 10) -> list[dict]:
    """Devuelve los últimos N mensajes ordenados cronológicamente."""
    res = (
        supabase.table("chat_messages")
        .select("role, content")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    # Invertir para orden cronológico (más antiguo primero)
    return list(reversed(res.data or []))


def get_session_messages(user_id: str) -> list[dict]:
    """Devuelve todos los mensajes de la sesión activa del usuario."""
    import json as _json
    res = (
        supabase.table("chat_sessions")
        .select("id")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return []

    session_id = res.data[0]["id"]
    msgs = (
        supabase.table("chat_messages")
        .select("role, content, created_at")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )

    result = []
    for m in (msgs.data or []):
        content = m["content"] or ""
        metadata = None
        # Separador ||META|| indica que hay metadata embebida
        if "||META||" in content:
            text, meta_str = content.split("||META||", 1)
            try:
                metadata = _json.loads(meta_str)
            except Exception:
                metadata = None
            content = text
        row = {"role": m["role"], "content": content, "created_at": m["created_at"]}
        if metadata:
            row["metadata"] = metadata
        result.append(row)
    return result


# ── Workout Library ───────────────────────────────────────────────────────────

def get_library_workouts(q: str | None = None, page: int = 1, limit: int = 20) -> list[dict]:
    """Lista paginada de plantillas. Filtra por title o tags si se proporciona q."""
    offset = (page - 1) * limit
    query = (
        supabase.table("workout_library")
        .select("id, title, description, sport_type, duration_min, intensity_level, tags, structure, nutrition_template, est_tss")
        .order("title")
        .range(offset, offset + limit - 1)
    )
    if q:
        # Filtro case-insensitive por title o tags
        query = query.or_(f"title.ilike.%{q}%,tags.cs.{{{q}}}")
    res = query.execute()
    return res.data or []


def get_library_workout_by_id(workout_id: str) -> dict | None:
    """Devuelve la plantilla completa por ID."""
    res = (
        supabase.table("workout_library")
        .select("id, title, description, sport_type, duration_min, intensity_level, tags, structure, nutrition_template, est_tss, embedding_status, created_at")
        .eq("id", workout_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def insert_library_workout(fields: dict) -> dict:
    """Inserta una nueva plantilla en la Workout Library."""
    res = (
        supabase.table("workout_library")
        .insert(fields)
        .execute()
    )
    return res.data[0] if res.data else {}


def update_library_workout(workout_id: str, fields: dict) -> dict:
    """Actualiza campos de una plantilla existente."""
    res = (
        supabase.table("workout_library")
        .update(fields)
        .eq("id", workout_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def schedule_library_workout(template_id: str, user_id: str, date: str) -> dict | None:
    """
    Crea un Planned_Workout a partir de una Workout_Template.
    Devuelve None si ya existe un entreno para esa fecha (conflicto 409).
    """
    # Verificar si ya existe un entreno para esa fecha
    existing = get_planned_workout(user_id, date)
    if existing:
        return None  # el caller debe devolver 409

    # Obtener la plantilla
    template = get_library_workout_by_id(template_id)
    if not template:
        return {}

    payload = {
        "user_id": user_id,
        "date": date,
        "title": template.get("title"),
        "description": template.get("description"),
        "planned_duration_s": (template.get("duration_min") or 0) * 60,
        "structure": template.get("structure"),
        "nutrition": template.get("nutrition_template"),
        "template_id": template_id,
        "status": "planned",
        "source": "library",
    }
    res = (
        supabase.table("planned_workouts")
        .insert(payload)
        .execute()
    )
    return res.data[0] if res.data else {}
