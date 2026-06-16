from datetime import date, timedelta
from db.supabase_client import supabase

# Mínimo de registros históricos para considerar la línea base fiable
WELLNESS_MIN_DAYS = 14


def _get_wellness_signals(user_id: str, today: date) -> dict:
    """
    Calcula señales de bienestar (HRV, FC reposo) como desviación respecto
    a la línea base personal del atleta.

    Solo devuelve datos si hay >= WELLNESS_MIN_DAYS registros históricos.
    Pasar valores absolutos sin línea base al agente sería ruido, no información.

    Returns dict con claves opcionales:
        hrv_signal:          "positive" | "neutral" | "negative"
        hrv_deviation_pct:   float  (% sobre línea base)
        hrv_today:           float  (valor absoluto, solo informativo)
        hrv_baseline:        float  (media 14 días)
        resting_hr_signal:   "positive" | "neutral" | "negative"
        resting_hr_deviation_pct: float
        wellness_days_available: int  (cuántos días hay en el histórico)
    """
    thirty_days_ago = (today - timedelta(days=30)).isoformat()

    res = (
        supabase.table("daily_metrics")
        .select("date, hrv, resting_hr")
        .eq("user_id", user_id)
        .gte("date", thirty_days_ago)
        .lte("date", today.isoformat())
        .order("date", desc=True)
        .execute()
    )
    rows = res.data or []

    today_str = today.isoformat()
    today_row = next((r for r in rows if r["date"] == today_str), None)
    history = [r for r in rows if r["date"] != today_str]

    result: dict = {"wellness_days_available": len(history)}

    if len(history) < WELLNESS_MIN_DAYS:
        # Sin suficiente historia, no incluir señales
        return result

    # ── HRV ──────────────────────────────────────────────────────────────────
    hrv_history = [float(r["hrv"]) for r in history if r.get("hrv") is not None]
    if len(hrv_history) >= WELLNESS_MIN_DAYS and today_row and today_row.get("hrv") is not None:
        baseline = sum(hrv_history[:WELLNESS_MIN_DAYS]) / WELLNESS_MIN_DAYS
        hrv_today = float(today_row["hrv"])
        deviation = ((hrv_today - baseline) / baseline) * 100

        result["hrv_today"] = hrv_today
        result["hrv_baseline"] = round(baseline, 1)
        result["hrv_deviation_pct"] = round(deviation, 1)

        # HRV alto = bien recuperado; HRV bajo = fatiga/estrés
        if deviation >= 5:
            result["hrv_signal"] = "positive"
        elif deviation <= -8:
            result["hrv_signal"] = "negative"
        else:
            result["hrv_signal"] = "neutral"

    # ── FC reposo ─────────────────────────────────────────────────────────────
    hr_history = [float(r["resting_hr"]) for r in history if r.get("resting_hr") is not None]
    if len(hr_history) >= WELLNESS_MIN_DAYS and today_row and today_row.get("resting_hr") is not None:
        baseline = sum(hr_history[:WELLNESS_MIN_DAYS]) / WELLNESS_MIN_DAYS
        hr_today = float(today_row["resting_hr"])
        deviation = ((hr_today - baseline) / baseline) * 100

        result["resting_hr_today"] = hr_today
        result["resting_hr_baseline"] = round(baseline, 1)
        result["resting_hr_deviation_pct"] = round(deviation, 1)

        # FC reposo alta = fatiga/estrés; FC reposo baja = bien recuperado
        if deviation >= 5:
            result["resting_hr_signal"] = "negative"
        elif deviation <= -5:
            result["resting_hr_signal"] = "positive"
        else:
            result["resting_hr_signal"] = "neutral"

    return result


def get_athlete_context(user_id: str, reference_date: str) -> dict:
    """
    Agrega todo el contexto del atleta en una sola llamada.
    """
    today = date.fromisoformat(reference_date)
    week_start = today - timedelta(days=today.weekday())  # lunes de esta semana
    week_end = week_start + timedelta(days=6)
    four_weeks_ago = today - timedelta(weeks=4)

    # ── Query 1: perfil del atleta ────────────────────────────────────────────
    profile_res = (
        supabase.table("users")
        .select("ftp, weight, max_heartrate, birthdate, goal, available_days")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    profile = (profile_res.data or [{}])[0]

    ftp = profile.get("ftp")
    weight = profile.get("weight")
    max_hr = profile.get("max_heartrate")
    birthdate = profile.get("birthdate")
    goal = profile.get("goal")
    available_days = profile.get("available_days", 5)

    age = None
    if birthdate:
        try:
            bd = date.fromisoformat(birthdate[:10])
            age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except Exception:
            pass

    w_per_kg = round(ftp / weight, 2) if ftp and weight and weight > 0 else None

    # ── Query 2: métricas recientes (CTL/ATL/TSB + promedios semanales) ───────
    # Buscar la fila exacta de hoy; si no existe, tomar la más reciente y proyectar
    metrics_res = (
        supabase.table("daily_metrics")
        .select("date, ctl, atl, tsb")
        .eq("user_id", user_id)
        .lte("date", reference_date)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    latest_row = (metrics_res.data or [{}])[0]

    # Si la fila más reciente no es de hoy, proyectar CTL/ATL hasta reference_date
    # usando TSS=0 para los días sin entreno (decaimiento natural)
    if latest_row and latest_row.get("date") and latest_row["date"] != reference_date:
        ctl = float(latest_row.get("ctl") or 0)
        atl = float(latest_row.get("atl") or 0)
        last_date = date.fromisoformat(latest_row["date"])
        days_gap = (today - last_date).days
        # Proyectar con TSS=0 cada día intermedio
        for _ in range(days_gap):
            ctl = ctl + (0 - ctl) / 42
            atl = atl + (0 - atl) / 7
        metrics_today = {
            "ctl": round(ctl, 2),
            "atl": round(atl, 2),
            "tsb": round(ctl - atl, 2),
        }
    else:
        metrics_today = latest_row

    # Calcular promedios de las últimas 4 semanas COMPLETAS (excluyendo la semana actual)
    # La semana actual empieza el lunes, así que buscamos semanas que terminaron antes del lunes actual
    weekly_res = (
        supabase.table("weekly_summaries")
        .select("completed_distance_km, completed_hours, completed_tss")
        .eq("user_id", user_id)
        .gte("week_start_date", four_weeks_ago.isoformat())
        .lt("week_start_date", week_start.isoformat())  # Excluir la semana actual
        .execute()
    )
    weekly_rows = weekly_res.data or []

    km_avg = hours_avg = tss_avg = None
    if weekly_rows:
        km_avg = round(sum(r["completed_distance_km"] for r in weekly_rows) / len(weekly_rows), 1)
        hours_avg = round(sum(r["completed_hours"] for r in weekly_rows) / len(weekly_rows), 1)
        tss_avg = round(sum(r["completed_tss"] for r in weekly_rows) / len(weekly_rows), 0)

    # ── Query 3: semana actual (planificados + realizados) + último entreno ───
    week_planned_res = (
        supabase.table("planned_workouts")
        .select("date, title, planned_duration_s, estimated_tss, status")
        .eq("user_id", user_id)
        .gte("date", week_start.isoformat())
        .lte("date", week_end.isoformat())
        .execute()
    )
    week_planned = week_planned_res.data or []

    week_done_res = (
        supabase.table("trainings")
        .select("date, name, duration, TSS")
        .eq("user_id", user_id)
        .gte("date", week_start.isoformat())
        .lte("date", today.isoformat())
        .order("date", desc=True)
        .execute()
    )
    week_done = week_done_res.data or []

    tss_week = sum(r.get("TSS") or 0 for r in week_done)
    last_training = week_done[0] if week_done else None

    # Si no hay entreno esta semana, buscar el último en general (con TSS)
    if not last_training:
        last_res = (
            supabase.table("trainings")
            .select("date, name, TSS")
            .eq("user_id", user_id)
            .lte("date", today.isoformat())
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        last_training = (last_res.data or [None])[0]

    # ── Query 4: próximo evento ───────────────────────────────────────────────
    event_res = (
        supabase.table("events")
        .select("name, date")
        .eq("user_id", user_id)
        .gte("date", today.isoformat())
        .order("date", desc=False)
        .limit(1)
        .execute()
    )
    next_event = (event_res.data or [None])[0]
    days_to_event = None
    if next_event:
        days_to_event = (date.fromisoformat(next_event["date"]) - today).days

    # ── Query 5: días bloqueados de la semana actual ──────────────────────────
    blocked_res = (
        supabase.table("blocked_days")
        .select("date, reason")
        .eq("user_id", user_id)
        .gte("date", week_start.isoformat())
        .lte("date", week_end.isoformat())
        .execute()
    )
    blocked_this_week = [
        {"date": r["date"], "reason": r.get("reason")}
        for r in (blocked_res.data or [])
    ]

    # ── Query 6: señales de bienestar (HRV / FC reposo) ───────────────────────
    wellness = _get_wellness_signals(user_id, today)

    return {
        # Perfil
        "ftp": ftp,
        "weight": weight,
        "w_per_kg": w_per_kg,
        "max_hr": max_hr,
        "age": age,
        "goal": goal,
        "available_days": available_days,
        # Carga reciente
        "ctl": metrics_today.get("ctl"),
        "atl": metrics_today.get("atl"),
        "tsb": metrics_today.get("tsb"),
        "km_avg_4w": km_avg,
        "hours_avg_4w": hours_avg,
        "tss_avg_4w": tss_avg,
        # Semana actual
        "tss_week": round(tss_week, 0),
        "done_this_week": len(week_done),
        "planned_this_week": [
            {
                "date": p["date"],
                "title": p["title"],
                "duration_min": (p.get("planned_duration_s") or 0) // 60,
                "estimated_tss": p.get("estimated_tss"),
            }
            for p in week_planned
        ],
        "last_training_date": last_training["date"] if last_training else None,
        "last_training_name": last_training.get("name") if last_training else None,
        "last_training_tss": last_training.get("TSS") if last_training else None,
        "last_training_type": last_training.get("workout_type") if last_training else None,
        # Próximo evento
        "next_event_name": next_event["name"] if next_event else None,
        "next_event_date": next_event["date"] if next_event else None,
        "next_event_days": days_to_event,
        "blocked_this_week": blocked_this_week,
        # Señales de bienestar (solo si hay >= 14 días de historia)
        **wellness,
    }


def format_context_for_prompt(ctx: dict) -> str:
    """Formatea el contexto del atleta como bloque de texto para los prompts."""
    lines = ["── Contexto del atleta ──────────────────────────────"]

    # Perfil
    ftp_str = f"{ctx['ftp']} W" if ctx['ftp'] else "no definido"
    weight_str = f"{ctx['weight']} kg" if ctx['weight'] else "no definido"
    wkg_str = f"{ctx['w_per_kg']} W/kg" if ctx['w_per_kg'] else "—"
    age_str = f"{ctx['age']} años" if ctx['age'] else "—"
    hr_str = f"{ctx['max_hr']} ppm" if ctx['max_hr'] else "—"
    goal_str = ctx['goal'] or "no especificado"
    days_str = str(ctx['available_days']) if ctx['available_days'] else "5"

    lines.append(f"FTP: {ftp_str} | Peso: {weight_str} | W/kg: {wkg_str}")
    lines.append(f"FC máxima: {hr_str} | Edad: {age_str}")
    lines.append(f"Objetivo: {goal_str} | Días disponibles: {days_str}/semana")

    # Próximo evento
    if ctx['next_event_name']:
        lines.append(f"Próximo evento: {ctx['next_event_name']} ({ctx['next_event_date']}, en {ctx['next_event_days']} días)")
    else:
        lines.append("Próximo evento: ninguno registrado")

    # Carga reciente
    lines.append("")
    ctl_str = f"{ctx['ctl']:.1f}" if ctx['ctl'] is not None else "—"
    atl_str = f"{ctx['atl']:.1f}" if ctx['atl'] is not None else "—"
    tsb_str = f"{ctx['tsb']:+.1f}" if ctx['tsb'] is not None else "—"
    lines.append(f"CTL (fitness): {ctl_str} | ATL (fatiga): {atl_str} | TSB (balance): {tsb_str}")

    if ctx['km_avg_4w'] is not None:
        lines.append(
            f"Promedio últimas 4 semanas: {ctx['km_avg_4w']} km/sem, "
            f"{ctx['hours_avg_4w']} h/sem, {int(ctx['tss_avg_4w'])} TSS/sem"
        )

    if ctx['last_training_date']:
        last_tss = ctx.get('last_training_tss')
        last_type = ctx.get('last_training_type', '')
        tss_str = f" | TSS: {int(last_tss)}" if last_tss else ""
        race_str = " [CARRERA/COMPETICIÓN]" if last_type and 'race' in str(last_type).lower() else ""
        lines.append(f"Último entreno: {ctx['last_training_date']} — {ctx['last_training_name'] or 'sin nombre'}{tss_str}{race_str}")

    # Semana actual
    lines.append("")
    lines.append(f"Esta semana: {ctx['done_this_week']} entrenos realizados | TSS acumulado: {int(ctx['tss_week'])}")

    if ctx['planned_this_week']:
        planned_str = ", ".join(
            f"{p['date']} {p['title']} ({p['duration_min']}min"
            + (f", ~{int(p['estimated_tss'])} TSS" if p.get('estimated_tss') else "")
            + ")"
            for p in ctx['planned_this_week']
        )
        lines.append(f"Planificado esta semana: {planned_str}")

    if ctx.get('blocked_this_week'):
        blocked_str = ", ".join(
            f"{b['date']}" + (f" ({b['reason']})" if b.get('reason') else "")
            for b in ctx['blocked_this_week']
        )
        lines.append(f"Días bloqueados esta semana: {blocked_str}")

    # Señales de bienestar (solo si hay suficiente historia)
    wellness_days = ctx.get("wellness_days_available", 0)
    has_hrv = ctx.get("hrv_signal") is not None
    has_hr = ctx.get("resting_hr_signal") is not None

    if has_hrv or has_hr:
        lines.append("")
        lines.append("Señales de bienestar de hoy (basadas en línea base personal):")

        if has_hrv:
            signal_map = {"positive": "↑ positiva (bien recuperado)", "neutral": "→ normal", "negative": "↓ negativa (fatiga/estrés)"}
            dev = ctx["hrv_deviation_pct"]
            sign = "+" if dev >= 0 else ""
            lines.append(f"  HRV: {sign}{dev}% sobre línea base ({ctx['hrv_baseline']} ms) → señal {signal_map[ctx['hrv_signal']]}")

        if has_hr:
            signal_map = {"positive": "↓ positiva (bien recuperado)", "neutral": "→ normal", "negative": "↑ negativa (fatiga/estrés)"}
            dev = ctx["resting_hr_deviation_pct"]
            sign = "+" if dev >= 0 else ""
            lines.append(f"  FC reposo: {sign}{dev}% sobre línea base ({ctx['resting_hr_baseline']} bpm) → señal {signal_map[ctx['resting_hr_signal']]}")

    elif wellness_days > 0:
        lines.append(f"  (Señales HRV/FC reposo no disponibles aún: {wellness_days}/{WELLNESS_MIN_DAYS} días registrados)")

    lines.append("─────────────────────────────────────────────────────")
    return "\n".join(lines)
