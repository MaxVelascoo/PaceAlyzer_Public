"""
import_zwo.py — Importa entrenos desde archivos .zwo (TrainingPeaks/Zwift) a la Workout Library.

Uso:
    cd PaceAlyzer_Backend
    python scripts/import_zwo.py scripts/workouts_import/

El script:
1. Parsea cada .zwo (XML determinista)
2. Convierte al formato JSON de la BD (structure, zonas Coggan)
3. Usa GPT para generar tags y nutrition_template (campos no presentes en .zwo)
4. Genera embedding canónico para recuperación semántica
5. Hace upsert en Supabase (idempotente por title)
"""

import sys
import os
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from html import unescape

# Añadir app al path para importar módulos del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from db.supabase_client import supabase
from llm.client import client, MODEL
from services.rag_service import rag_service


# ── Mapeo de potencia (% FTP) a zona Coggan ──────────────────────────────────

def power_to_zone(power_ratio: float) -> str:
    if power_ratio < 0.55:
        return "Z1"
    elif power_ratio < 0.75:
        return "Z2"
    elif power_ratio < 0.87:
        return "Z3"
    elif power_ratio < 0.95:
        return "Z4"
    elif power_ratio < 1.05:
        return "Z5"
    elif power_ratio < 1.20:
        return "Z6"
    else:
        return "Z7"


def power_to_intensity_level(max_power: float) -> str:
    if max_power < 0.75:
        return "recovery"
    elif max_power < 0.87:
        return "easy"
    elif max_power < 0.95:
        return "moderate"
    elif max_power < 1.10:
        return "hard"
    else:
        return "very_hard"


def zone_label(zone: str) -> str:
    labels = {
        "Z1": "Recuperación activa",
        "Z2": "Base aeróbica",
        "Z3": "Tempo",
        "Z4": "Umbral / Sweetspot",
        "Z5": "VO2max",
        "Z6": "Anaeróbico",
        "Z7": "Neuromuscular",
    }
    return labels.get(zone, zone)


# ── Cálculo de TSS estimado (algoritmo estándar con media móvil 30s) ─────────
# Basado en calcular_estTSS.yaml — resolución 1 segundo, NP con ventana 30s

def estimate_tss_from_zwo_xml(workout_el) -> float | None:
    """
    Calcula el TSS estimado directamente desde el elemento XML <workout>.
    Expande cada nodo a una serie temporal de 1 segundo y aplica la
    media móvil de 30s para calcular NP/IF/TSS según el estándar TrainingPeaks.

    Soporta: SteadyState, IntervalsT, Warmup, Cooldown, Ramp, FreeRide.
    Nodos desconocidos se ignoran con log.
    """
    series = []

    for node in workout_el:
        tag = node.tag

        if tag == "SteadyState":
            duration = int(float(node.attrib.get("Duration", 0)))
            power = float(node.attrib.get("Power", 0.65))
            series.extend([power] * duration)

        elif tag == "IntervalsT":
            repeat = int(node.attrib.get("Repeat", 1))
            on_dur = int(float(node.attrib.get("OnDuration", 60)))
            on_pow = float(node.attrib.get("OnPower", 0.9))
            off_dur = int(float(node.attrib.get("OffDuration", 60)))
            off_pow = float(node.attrib.get("OffPower", 0.5))
            for _ in range(repeat):
                series.extend([on_pow] * on_dur)
                series.extend([off_pow] * off_dur)

        elif tag in ("Warmup", "Cooldown"):
            duration = int(float(node.attrib.get("Duration", 0)))
            p_low = float(node.attrib.get("PowerLow", 0.5))
            p_high = float(node.attrib.get("PowerHigh", 0.7))
            avg = (p_low + p_high) / 2
            series.extend([avg] * duration)

        elif tag == "Ramp":
            duration = int(float(node.attrib.get("Duration", 0)))
            p_low = float(node.attrib.get("PowerLow", 0.5))
            p_high = float(node.attrib.get("PowerHigh", 1.0))
            # Interpolar linealmente segundo a segundo
            if duration > 0:
                for i in range(duration):
                    p = p_low + (p_high - p_low) * i / (duration - 1) if duration > 1 else p_low
                    series.append(p)

        elif tag == "FreeRide":
            duration = int(float(node.attrib.get("Duration", 0)))
            series.extend([0.65] * duration)  # Z2 por defecto

        else:
            # Nodo desconocido — ignorar silenciosamente
            pass

    N = len(series)
    if N < 30:
        return None

    # Media móvil de 30s con suma deslizante (eficiente)
    window_sum = sum(series[:30])
    moving = [window_sum / 30.0]
    for i in range(30, N):
        window_sum += series[i] - series[i - 30]
        moving.append(window_sum / 30.0)

    mean_fourth = sum(x ** 4 for x in moving) / len(moving)
    intensity_factor = mean_fourth ** 0.25
    tss = 100.0 * (N / 3600.0) * (intensity_factor ** 2)

    return round(tss, 1)


def estimate_tss_from_structure(steps: list, duration_s: int) -> float:
    """Fallback cuando no hay acceso al XML original — usa potencias de la structure."""
    power_samples = []

    def walk(step_list):
        for step in step_list:
            if step.get("type") == "interval":
                target = step.get("target", {})
                dur = step.get("duration_s", 0)
                if dur == 0:
                    continue
                if "power" in target:
                    p = float(target["power"])
                elif "power_low" in target and "power_high" in target:
                    p = (float(target["power_low"]) + float(target["power_high"])) / 2
                else:
                    zone_power = {"Z1": 0.50, "Z2": 0.65, "Z3": 0.81, "Z4": 0.91,
                                  "Z5": 1.00, "Z6": 1.12, "Z7": 1.30}
                    p = zone_power.get(target.get("zone", "Z2"), 0.65)
                power_samples.append((p, dur))
            elif step.get("type") == "repeat":
                for _ in range(step.get("repeat", 1)):
                    walk(step.get("steps", []))

    walk(steps)
    if not power_samples:
        return 50.0

    total_dur = sum(d for _, d in power_samples)
    if total_dur == 0:
        return 50.0

    # Expandir a serie de 1s para aplicar el mismo algoritmo
    series = []
    for p, d in power_samples:
        series.extend([p] * d)

    N = len(series)
    if N < 30:
        return 50.0

    window_sum = sum(series[:30])
    moving = [window_sum / 30.0]
    for i in range(30, N):
        window_sum += series[i] - series[i - 30]
        moving.append(window_sum / 30.0)

    mean_fourth = sum(x ** 4 for x in moving) / len(moving)
    intensity_factor = mean_fourth ** 0.25
    tss = 100.0 * (N / 3600.0) * (intensity_factor ** 2)
    return round(tss, 1)


# ── Detección de patrones repetidos en lista plana de steps ──────────────────

def detect_repeats(steps: list) -> list:
    """
    Detecta secuencias repetidas en una lista plana de steps y las agrupa
    en bloques 'repeat'. Busca el patrón más largo que se repite ≥ 2 veces.

    Ejemplo: [A, B, A, B, A, B] → [repeat(3, [A, B])]
    """
    if len(steps) < 2:
        return steps

    def steps_equal(a: dict, b: dict) -> bool:
        """Compara dos steps por zona y duración (ignora label e instructions)."""
        if a.get("type") != b.get("type"):
            return False
        if a.get("duration_s") != b.get("duration_s"):
            return False
        a_zone = (a.get("target") or {}).get("zone")
        b_zone = (b.get("target") or {}).get("zone")
        return a_zone == b_zone

    def pattern_matches(steps: list, start: int, pattern_len: int, repeat_count: int) -> bool:
        """Verifica si el patrón de longitud pattern_len se repite repeat_count veces desde start."""
        pattern = steps[start:start + pattern_len]
        for r in range(1, repeat_count):
            offset = start + r * pattern_len
            if offset + pattern_len > len(steps):
                return False
            for i in range(pattern_len):
                if not steps_equal(pattern[i], steps[offset + i]):
                    return False
        return True

    result = []
    i = 0
    while i < len(steps):
        best_pattern_len = 1
        best_repeat_count = 1

        # Buscar el mejor patrón (más repeticiones * longitud) desde posición i
        for pattern_len in range(1, (len(steps) - i) // 2 + 1):
            repeat_count = 1
            while pattern_matches(steps, i, pattern_len, repeat_count + 1):
                repeat_count += 1
            if repeat_count > 1:
                score = repeat_count * pattern_len
                best_score = best_repeat_count * best_pattern_len
                if score > best_score:
                    best_pattern_len = pattern_len
                    best_repeat_count = repeat_count

        if best_repeat_count > 1:
            pattern = steps[i:i + best_pattern_len]
            on_step = pattern[0]
            on_zone = (on_step.get("target") or {}).get("zone", "Z4")
            on_dur = on_step.get("duration_s", 0)
            label = f"{best_repeat_count}x{on_dur // 60}' {zone_label(on_zone)}" if on_dur >= 60 else f"{best_repeat_count}x{on_dur}\" {zone_label(on_zone)}"
            result.append({
                "type": "repeat",
                "label": label,
                "repeat": best_repeat_count,
                "steps": pattern,
            })
            i += best_pattern_len * best_repeat_count
        else:
            result.append(steps[i])
            i += 1

    return result


# ── Parser .zwo → estructura interna ─────────────────────────────────────────

def parse_zwo(filepath: Path) -> dict | None:
    """Parsea un archivo .zwo y devuelve un dict con los campos de la BD."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"  ✗ Error parseando XML: {e}")
        return None

    title = unescape(root.findtext("name") or filepath.stem)
    description = unescape(root.findtext("description") or "")

    workout_el = root.find("workout")
    if workout_el is None:
        print(f"  ✗ No se encontró elemento <workout>")
        return None

    steps = []
    max_power = 0.0
    total_duration_s = 0

    for el in workout_el:
        tag = el.tag

        if tag == "Warmup":
            dur = int(float(el.get("Duration", 0)))
            p_low = float(el.get("PowerLow", 0.5))
            p_high = float(el.get("PowerHigh", 0.7))
            avg_power = (p_low + p_high) / 2
            zone = power_to_zone(avg_power)
            max_power = max(max_power, p_high)
            total_duration_s += dur
            steps.append({
                "type": "interval",
                "label": "Calentamiento",
                "duration_s": dur,
                "target": {"zone": zone, "power_low": p_low, "power_high": p_high},
                "instructions": f"Calentamiento progresivo {zone_label(zone)}",
            })

        elif tag == "Cooldown":
            dur = int(float(el.get("Duration", 0)))
            p_low = float(el.get("PowerLow", 0.5))
            p_high = float(el.get("PowerHigh", 0.7))
            avg_power = (p_low + p_high) / 2
            zone = power_to_zone(avg_power)
            total_duration_s += dur
            steps.append({
                "type": "interval",
                "label": "Vuelta a la calma",
                "duration_s": dur,
                "target": {"zone": zone, "power_low": p_low, "power_high": p_high},
                "instructions": f"Recuperación progresiva {zone_label(zone)}",
            })

        elif tag == "SteadyState":
            dur = int(float(el.get("Duration", 0)))
            power = float(el.get("Power", 0.75))
            zone = power_to_zone(power)
            max_power = max(max_power, power)
            total_duration_s += dur
            steps.append({
                "type": "interval",
                "label": zone_label(zone),
                "duration_s": dur,
                "target": {"zone": zone, "power": power},
                "instructions": f"Mantén potencia constante en {zone_label(zone)} ({int(power*100)}% FTP)",
            })

        elif tag == "IntervalsT":
            repeat = int(el.get("Repeat", 1))
            on_dur = int(float(el.get("OnDuration", 60)))
            on_power = float(el.get("OnPower", 0.9))
            off_dur = int(float(el.get("OffDuration", 60)))
            off_power = float(el.get("OffPower", 0.5))
            on_zone = power_to_zone(on_power)
            off_zone = power_to_zone(off_power)
            max_power = max(max_power, on_power)
            total_duration_s += repeat * (on_dur + off_dur)
            steps.append({
                "type": "repeat",
                "label": f"{repeat}x{on_dur//60}' {zone_label(on_zone)}",
                "repeat": repeat,
                "steps": [
                    {
                        "type": "interval",
                        "label": zone_label(on_zone),
                        "duration_s": on_dur,
                        "target": {"zone": on_zone, "power": on_power},
                        "instructions": f"{zone_label(on_zone)} al {int(on_power*100)}% FTP",
                    },
                    {
                        "type": "interval",
                        "label": "Recuperación",
                        "duration_s": off_dur,
                        "target": {"zone": off_zone, "power": off_power},
                        "instructions": f"Recuperación activa al {int(off_power*100)}% FTP",
                    },
                ],
            })

        elif tag == "FreeRide":
            dur = int(float(el.get("Duration", 0)))
            total_duration_s += dur
            steps.append({
                "type": "interval",
                "label": "Rodaje libre",
                "duration_s": dur,
                "target": {"zone": "Z2"},
                "instructions": "Ritmo libre, escucha tu cuerpo",
            })

        elif tag == "Ramp":
            dur = int(float(el.get("Duration", 0)))
            p_low = float(el.get("PowerLow", 0.5))
            p_high = float(el.get("PowerHigh", 1.0))
            max_power = max(max_power, p_high)
            total_duration_s += dur
            steps.append({
                "type": "interval",
                "label": "Rampa de potencia",
                "duration_s": dur,
                "target": {"zone": power_to_zone((p_low + p_high) / 2), "power_low": p_low, "power_high": p_high},
                "instructions": f"Incrementa progresivamente de {int(p_low*100)}% a {int(p_high*100)}% FTP",
            })

    if not steps:
        print(f"  ✗ No se encontraron steps en el workout")
        return None

    # Separar warmup/cooldown del bloque principal para detectar repeticiones solo en el medio
    warmup_steps = [s for s in steps if s.get("label") == "Calentamiento"]
    cooldown_steps = [s for s in steps if s.get("label") == "Vuelta a la calma"]
    main_steps = [s for s in steps if s.get("label") not in ("Calentamiento", "Vuelta a la calma")]

    # Detectar patrones repetidos en el bloque principal
    main_steps_grouped = detect_repeats(main_steps)

    steps = warmup_steps + main_steps_grouped + cooldown_steps

    duration_min = total_duration_s // 60
    intensity_level = power_to_intensity_level(max_power)
    # Calcular TSS con el algoritmo estándar de media móvil 30s directamente desde el XML
    est_tss = estimate_tss_from_zwo_xml(workout_el)
    if est_tss is None:
        est_tss = estimate_tss_from_structure(steps, total_duration_s)

    structure = {
        "schema_version": 1,
        "intensity_model": "power_zones",
        "zone_system": "coggan_7",
        "session": {
            "goal": title,
            "description": description,
            "execution_notes": [],
            "warnings": [],
        },
        "steps": steps,
    }

    return {
        "title": title,
        "description": description,
        "sport_type": "cycling",
        "duration_min": duration_min,
        "intensity_level": intensity_level,
        "structure": structure,
        "est_tss": est_tss,
        "_max_power": max_power,  # campo temporal para el LLM
    }


# ── Enriquecimiento con LLM (tags + nutrition_template) ──────────────────────

def enrich_with_llm(workout: dict) -> dict:
    """Usa GPT para generar tags y nutrition_template."""
    prompt = f"""Dado este entreno de ciclismo, genera:
1. Una lista de 3-6 tags descriptivos (en español, minúsculas)
2. Una nutrition_template con valores de referencia

Entreno:
- Título: {workout['title']}
- Descripción: {workout['description']}
- Duración: {workout['duration_min']} minutos
- Intensidad: {workout['intensity_level']}
- TSS estimado: {workout['est_tss']}
- Potencia máxima: {int(workout['_max_power'] * 100)}% FTP

Responde SOLO con JSON válido:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "nutrition_template": {{
    "pre": {{"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2}},
    "during": {{"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0}},
    "post": {{"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.4}}
  }}
}}

Guía de nutrición según intensidad:
- recovery/easy: pre carbs 0.5-1.0 g/kg, during 30-45 g/h, post carbs 0.8-1.0 g/kg
- moderate: pre carbs 1.0-1.5 g/kg, during 45-60 g/h, post carbs 1.0-1.2 g/kg  
- hard: pre carbs 1.5-2.0 g/kg, during 60-80 g/h, post carbs 1.2-1.5 g/kg
- very_hard: pre carbs 2.0-2.5 g/kg, during 80-90 g/h, post carbs 1.5-2.0 g/kg"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=300,
    )
    data = json.loads(response.choices[0].message.content)
    workout["tags"] = data.get("tags", [])
    workout["nutrition_template"] = data.get("nutrition_template")
    del workout["_max_power"]
    return workout


# ── Upsert en Supabase ────────────────────────────────────────────────────────

def upsert_workout(workout: dict) -> str:
    """Inserta o actualiza la plantilla. Devuelve el ID."""
    existing = (
        supabase.table("workout_library")
        .select("id")
        .eq("title", workout["title"])
        .limit(1)
        .execute()
    )

    if existing.data:
        workout_id = existing.data[0]["id"]
        supabase.table("workout_library").update(workout).eq("id", workout_id).execute()
        return workout_id
    else:
        # Solo marcar pending si no hay embedding ya generado
        if "embedding" not in workout or workout.get("embedding") is None:
            workout["embedding_status"] = "pending"
        res = supabase.table("workout_library").insert(workout).execute()
        return res.data[0]["id"]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_zwo.py <carpeta_o_archivo.zwo>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if target.is_dir():
        files = sorted(target.glob("*.zwo"))
    elif target.suffix == ".zwo":
        files = [target]
    else:
        print(f"Error: {target} no es un .zwo ni una carpeta")
        sys.exit(1)

    if not files:
        print(f"No se encontraron archivos .zwo en {target}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Importando {len(files)} archivo(s) .zwo")
    print(f"{'='*60}\n")

    errors = []
    t_start = time.monotonic()

    for i, filepath in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {filepath.name}")

        # 1. Parsear .zwo
        workout = parse_zwo(filepath)
        if not workout:
            errors.append(filepath.name)
            continue

        print(f"  ✓ Parseado: {workout['title']} ({workout['duration_min']}min, {workout['intensity_level']}, ~{workout['est_tss']} TSS)")

        # 2. Enriquecer con LLM (tags + nutrition)
        try:
            workout = enrich_with_llm(workout)
            print(f"  ✓ Tags: {workout['tags']}")
        except Exception as e:
            print(f"  ⚠ LLM falló, usando defaults: {e}")
            workout["tags"] = []
            workout["nutrition_template"] = None
            del workout["_max_power"]

        # 3. Generar embedding
        try:
            embedding = rag_service.generate_template_embedding(workout)
            if embedding:
                workout["embedding"] = embedding
                workout["embedding_status"] = "ready"
                print(f"  ✓ Embedding generado ({len(embedding)} dims)")
            else:
                workout["embedding_status"] = "error"
                print(f"  ⚠ Embedding falló, se guardará sin vector")
        except Exception as e:
            print(f"  ⚠ Embedding error: {e}")
            workout["embedding_status"] = "error"

        # 4. Upsert en Supabase
        try:
            workout_id = upsert_workout(workout)
            print(f"  ✓ Guardado en BD (id: {workout_id})\n")
        except Exception as e:
            print(f"  ✗ Error guardando en BD: {e}\n")
            errors.append(filepath.name)

    elapsed = time.monotonic() - t_start
    print(f"{'='*60}")
    print(f"Completado en {elapsed:.1f}s — {len(files) - len(errors)}/{len(files)} importados")
    if errors:
        print(f"Errores: {', '.join(errors)}")
        with open("seed_errors.log", "a") as f:
            for e in errors:
                f.write(f"{e}\n")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
