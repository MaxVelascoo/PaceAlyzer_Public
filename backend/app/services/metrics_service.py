from datetime import date, timedelta
from collections import defaultdict
from db.supabase_client import supabase
from utils.logger import logger


# ── Duraciones estándar para la curva MMP (en segundos) ──────────────────────

MMP_DURATIONS = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]


def calculate_mmp(power_stream: list[int | float]) -> dict[str, int] | None:
    """Calcula la potencia media máxima para cada duración estándar."""
    if not power_stream or len(power_stream) < 5:
        return None
    curve: dict[str, int] = {}
    for dur in MMP_DURATIONS:
        if dur > len(power_stream):
            break
        max_avg = 0.0
        for i in range(len(power_stream) - dur + 1):
            avg = sum(power_stream[i:i + dur]) / dur
            if avg > max_avg:
                max_avg = avg
        if max_avg > 0:
            curve[str(dur)] = round(max_avg)
    return curve if curve else None


def merge_best_mmp(existing: dict | None, new_curve: dict) -> dict:
    """Actualiza el histórico manteniendo el máximo por duración."""
    merged = dict(existing or {})
    for dur, watts in new_curve.items():
        if dur not in merged or watts > merged[dur]:
            merged[dur] = watts
    return merged


def recalculate_mmp_history(user_id: str) -> dict:
    """
    Recalcula mmp_curve para todos los entrenamientos con power_stream
    y reconstruye best_mmp_curve en users desde cero.
    """
    import time
    t0 = time.monotonic()
    logger.agent_start("MmpRecalculator", {"user_id": user_id[:8]})

    # Leer todos los entrenamientos con power_stream
    res = (
        supabase.table("trainings")
        .select("activity_id, power_stream")
        .eq("user_id", user_id)
        .not_.is_("power_stream", "null")
        .execute()
    )
    rows = res.data or []

    best_mmp: dict = {}
    updated = 0

    for row in rows:
        stream = row.get("power_stream") or []
        if not stream:
            continue

        curve = calculate_mmp(stream)
        if not curve:
            continue

        # Guardar mmp_curve en el entreno
        supabase.table("trainings").update(
            {"mmp_curve": curve}
        ).eq("activity_id", row["activity_id"]).execute()

        # Actualizar el mejor histórico
        best_mmp = merge_best_mmp(best_mmp, curve)
        updated += 1

    # Guardar best_mmp_curve en users
    if best_mmp:
        supabase.table("users").update(
            {"best_mmp_curve": best_mmp}
        ).eq("id", user_id).execute()

    logger.agent_end("MmpRecalculator", int((time.monotonic() - t0) * 1000), {
        "trainings_processed": updated,
        "durations_in_curve": len(best_mmp),
    })

    return {
        "trainings_processed": updated,
        "best_mmp_curve": best_mmp,
    }


# ── Clasificación de zonas ────────────────────────────────────────────────────

def classify_power_zone(watts: float, ftp: float) -> str:
    """Coggan 7 zonas basadas en % FTP."""
    pct = watts / ftp
    if pct < 0.55:   return "z1"
    if pct < 0.75:   return "z2"
    if pct < 0.90:   return "z3"
    if pct < 1.05:   return "z4"
    if pct < 1.20:   return "z5"
    if pct < 1.50:   return "z6"
    return "z7"


def classify_hr_zone(bpm: float, max_hr: float) -> str:
    """Friel 5 zonas basadas en % FC máxima."""
    pct = bpm / max_hr
    if pct < 0.60:   return "z1"
    if pct < 0.70:   return "z2"
    if pct < 0.80:   return "z3"
    if pct < 0.90:   return "z4"
    return "z5"


def compute_zones_from_streams(
    trainings: list[dict],
    ftp: float | None,
    max_hr: float | None,
) -> tuple[dict, dict]:
    """
    Suma los segundos en cada zona de potencia y FC para una lista de entrenamientos.
    Devuelve (power_zones_minutes, hr_zones_minutes) en minutos (float).
    """
    power_secs: dict[str, float] = {f"z{i}": 0.0 for i in range(1, 8)}
    hr_secs: dict[str, float] = {f"z{i}": 0.0 for i in range(1, 6)}

    for t in trainings:
        if ftp and ftp > 0:
            stream = t.get("power_stream") or []
            for w in stream:
                if w is not None and w > 0:
                    z = classify_power_zone(float(w), ftp)
                    power_secs[z] += 1

        if max_hr and max_hr > 0:
            stream = t.get("hr_stream") or []
            for bpm in stream:
                if bpm is not None and bpm > 0:
                    z = classify_hr_zone(float(bpm), max_hr)
                    hr_secs[z] += 1

    # Convertir segundos → minutos redondeados
    power_min = {k: round(v / 60, 1) for k, v in power_secs.items()}
    hr_min = {k: round(v / 60, 1) for k, v in hr_secs.items()}
    return power_min, hr_min


# ── Servicio principal ────────────────────────────────────────────────────────

def recalculate_metrics(user_id: str) -> dict:
    """
    Recalcula daily_metrics y weekly_summaries para el usuario.
    Se llama tras cada sync de Strava.
    """
    import time
    t0 = time.monotonic()
    logger.agent_start("MetricsService", {"user_id": user_id[:8]})

    # 1. Leer perfil del usuario (FTP y FC máxima para zonas)
    profile_res = (
        supabase.table("users")
        .select("ftp, max_heartrate")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    profile = profile_res.data or {}
    ftp = float(profile.get("ftp") or 0) or None
    max_hr = float(profile.get("max_heartrate") or 0) or None

    # 2. Leer todos los entrenamientos (con streams para zonas)
    res = (
        supabase.table("trainings")
        .select("date, TSS, duration, distance, power_stream, hr_stream")
        .eq("user_id", user_id)
        .order("date", desc=False)
        .execute()
    )
    rows = res.data or []

    if not rows:
        return {"days_calculated": 0, "weeks_calculated": 0, "message": "No hay actividades"}

    # 3. Construir mapas por fecha
    tss_map: dict[str, float] = {}
    duration_map: dict[str, float] = defaultdict(float)
    distance_map: dict[str, float] = defaultdict(float)
    sessions_map: dict[str, int] = defaultdict(int)
    trainings_by_date: dict[str, list[dict]] = defaultdict(list)

    for r in rows:
        d = r.get("date")
        if not d:
            continue
        tss = r.get("TSS")
        if tss is not None:
            tss_map[d] = float(tss)
        duration_map[d] += float(r.get("duration") or 0)
        distance_map[d] += float(r.get("distance") or 0)
        sessions_map[d] += 1
        trainings_by_date[d].append(r)

    # 4. Calcular daily_metrics (CTL/ATL/TSB)
    first_date = date.fromisoformat(rows[0]["date"])
    today = date.today()

    ctl = 0.0
    atl = 0.0
    daily_metrics: list[dict] = []
    ctl_by_date: dict[str, float] = {}
    atl_by_date: dict[str, float] = {}

    current = first_date
    while current <= today:
        iso = current.isoformat()
        tss = tss_map.get(iso, 0.0)
        ctl = ctl + (tss - ctl) / 42
        atl = atl + (tss - atl) / 7
        ctl_by_date[iso] = ctl
        atl_by_date[iso] = atl
        daily_metrics.append({
            "user_id": user_id,
            "date": iso,
            "tss": round(tss, 2),
            "ctl": round(ctl, 2),
            "atl": round(atl, 2),
            "tsb": round(ctl - atl, 2),
        })
        current += timedelta(days=1)

    for i in range(0, len(daily_metrics), 500):
        supabase.table("daily_metrics").upsert(
            daily_metrics[i:i + 500], on_conflict="user_id,date"
        ).execute()

    # 5. Calcular weekly_summaries con zonas
    weeks: dict[tuple, list[str]] = defaultdict(list)
    current = first_date
    while current <= today:
        iso_year, iso_week, _ = current.isocalendar()
        weeks[(iso_year, iso_week)].append(current.isoformat())
        current += timedelta(days=1)

    weekly_rows: list[dict] = []
    for (iso_year, iso_week), day_list in sorted(weeks.items()):
        week_start = date.fromisoformat(day_list[0])
        week_end = date.fromisoformat(day_list[-1])

        # No calcular semanas que aún no han empezado
        if week_start > today:
            continue

        # Recopilar todos los entrenamientos de la semana
        week_trainings = []
        for d in day_list:
            week_trainings.extend(trainings_by_date.get(d, []))

        # Calcular zonas
        power_zones, hr_zones = compute_zones_from_streams(week_trainings, ftp, max_hr)

        last_day = day_list[-1]
        ctl_end = ctl_by_date.get(last_day, 0.0)
        atl_end = atl_by_date.get(last_day, 0.0)

        weekly_rows.append({
            "user_id": user_id,
            "week_start_date": week_start.isoformat(),
            "week_end_date": week_end.isoformat(),
            "iso_year": iso_year,
            "iso_week": iso_week,
            "completed_sessions_count": sum(sessions_map[d] for d in day_list),
            "completed_hours": round(sum(duration_map[d] for d in day_list) / 3600, 2),
            "completed_distance_km": round(sum(distance_map[d] for d in day_list) / 1000, 2),
            "completed_tss": round(sum(tss_map.get(d, 0.0) for d in day_list), 2),
            "ctl_end": round(ctl_end, 2),
            "atl_end": round(atl_end, 2),
            "tsb_end": round(ctl_end - atl_end, 2),
            "power_zones_minutes": power_zones,
            "hr_zones_minutes": hr_zones,
        })

    for i in range(0, len(weekly_rows), 200):
        supabase.table("weekly_summaries").upsert(
            weekly_rows[i:i + 200], on_conflict="user_id,iso_year,iso_week"
        ).execute()

    logger.agent_end("MetricsService", int((time.monotonic() - t0) * 1000), {
        "days_calculated": len(daily_metrics),
        "weeks_calculated": len(weekly_rows),
        "last_ctl": round(ctl, 1),
        "ftp_used": ftp,
        "max_hr_used": max_hr,
    })

    return {
        "days_calculated": len(daily_metrics),
        "weeks_calculated": len(weekly_rows),
        "first_date": first_date.isoformat(),
        "last_ctl": round(ctl, 1),
        "last_atl": round(atl, 1),
        "last_tsb": round(ctl - atl, 1),
    }
