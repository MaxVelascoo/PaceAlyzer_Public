# Porcentaje de FTP por zona Coggan (punto medio de cada zona)
# Usado para estimar la potencia normalizada de un entreno planificado
ZONE_FTP_PCT: dict[str, float] = {
    "Z1": 0.50,   # < 55% → usamos 50%
    "Z2": 0.65,   # 55-75% → usamos 65%
    "Z3": 0.83,   # 75-90% → usamos 83%
    "Z4": 0.975,  # 90-105% → usamos 97.5%
    "Z5": 1.125,  # 105-120% → usamos 112.5%
    "Z6": 1.35,   # 120-150% → usamos 135%
    "Z7": 1.75,   # > 150% → usamos 175%
}


def _flatten_steps(steps: list) -> list[tuple[str, int]]:
    """
    Expande la estructura de pasos en una lista plana de (zona, duration_s),
    expandiendo los bloques repeat.
    """
    result: list[tuple[str, int]] = []
    for step in steps:
        if step.get("type") == "interval":
            target = step.get("target", {})
            zone = target.get("zone") or target.get("zone_max") or target.get("zone_min") or "Z2"
            duration = step.get("duration_s", 0)
            result.append((zone, duration))
        elif step.get("type") == "repeat":
            children = _flatten_steps(step.get("steps", []))
            for _ in range(step.get("repeat", 1)):
                result.extend(children)
    return result


def estimate_tss(structure: dict, ftp: float) -> float | None:
    """
    Estima el TSS de un entreno planificado a partir de su estructura y el FTP del atleta.

    Método:
      1. Expande todos los pasos en (zona, duration_s)
      2. Convierte cada zona a watts estimados (% FTP × FTP)
      3. Calcula NP estimado como media ponderada por duración
      4. TSS = (duration_s × NP × IF) / (FTP × 3600) × 100

    Devuelve None si no hay estructura válida o FTP es 0.
    """
    if not ftp or ftp <= 0 or not structure:
        return None

    steps = structure.get("steps", [])
    if not steps:
        return None

    flat = _flatten_steps(steps)
    if not flat:
        return None

    total_duration = sum(d for _, d in flat)
    if total_duration <= 0:
        return None

    # Potencia media ponderada por duración
    weighted_watts = sum(
        ZONE_FTP_PCT.get(zone, 0.65) * ftp * duration
        for zone, duration in flat
    )
    avg_power = weighted_watts / total_duration

    # NP estimado ≈ avg_power para entrenamientos constantes,
    # pero para intervalos aplicamos un factor de variabilidad conservador
    # basado en la dispersión de zonas
    zones_used = {zone for zone, _ in flat}
    has_high_intensity = any(z in zones_used for z in ("Z5", "Z6", "Z7"))
    vi_factor = 1.05 if has_high_intensity else 1.02
    np_estimated = avg_power * vi_factor

    intensity_factor = np_estimated / ftp
    tss = (total_duration * np_estimated * intensity_factor) / (ftp * 3600) * 100

    return round(tss, 1)
