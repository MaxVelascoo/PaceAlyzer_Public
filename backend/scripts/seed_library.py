"""
Seed script for ~100 cycling workout templates.
Run from PaceAlyzer_Backend directory:
    python scripts/seed_library.py
"""
import sys
import os
import time
import json
import logging

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from db.supabase_client import supabase
from services.rag_service import RAGService

# ── Error logger ──────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "..", "seed_errors.log"),
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
)
seed_logger = logging.getLogger("seed_library")

rag = RAGService()

# ── Templates ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    # ── Z1 Recovery (5) ──────────────────────────────────────────────────────
    {
        "title": "Z1 Easy Spin 30min",
        "description": "Rodaje suave de recuperación activa. Cadencia alta, sin esfuerzo.",
        "sport_type": "cycling",
        "duration_min": 30,
        "intensity_level": "recovery",
        "tags": ["z1", "recovery", "easy_spin", "active_recovery"],
        "structure": {
            "schema_version": 1,
            "intensity_model": "power_zones",
            "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación activa post-esfuerzo",
                "description": "Pedaleo suave para acelerar la recuperación muscular.",
                "execution_notes": ["Cadencia 90-100 rpm", "Sin presión en los pedales"],
                "warnings": ["Detente si sientes dolor muscular agudo"],
            },
            "steps": [
                {"type": "interval", "label": "Rodaje Z1", "duration_s": 1800,
                 "target": {"zone": "Z1"}, "instructions": "Cadencia alta, esfuerzo mínimo"},
            ],
        },
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 0, "sodium_mg_per_hour": 0},
            "post": {"carbs_g_per_kg": 0.8, "protein_g_per_kg": 0.2},
        },
        "est_tss": 15.0,
    },
    {
        "title": "Z1 Active Recovery 45min",
        "description": "Recuperación activa de 45 minutos. Ideal el día después de una sesión dura.",
        "sport_type": "cycling",
        "duration_min": 45,
        "intensity_level": "recovery",
        "tags": ["z1", "recovery", "active_recovery", "post_race"],
        "structure": {
            "schema_version": 1,
            "intensity_model": "power_zones",
            "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación activa",
                "description": "Sesión de baja intensidad para limpiar lactato y reducir fatiga.",
                "execution_notes": ["Mantén Z1 estricto", "Cadencia 90+ rpm"],
                "warnings": ["No superes Z1 en ningún momento"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento suave", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Muy suave"},
                {"type": "interval", "label": "Rodaje recuperación", "duration_s": 1800,
                 "target": {"zone": "Z1"}, "instructions": "Constante y relajado"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 300,
                 "target": {"zone": "Z1"}, "instructions": "Reduce cadencia gradualmente"},
            ],
        },
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 0, "sodium_mg_per_hour": 200},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "est_tss": 22.0,
    },
    {
        "title": "Z1 Flush Ride 60min",
        "description": "Rodaje de descarga de 60 minutos. Perfecto para días de recuperación entre bloques.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "recovery",
        "tags": ["z1", "recovery", "flush", "easy"],
        "structure": {
            "schema_version": 1,
            "intensity_model": "power_zones",
            "zone_system": "coggan_7",
            "session": {
                "goal": "Descarga y recuperación",
                "description": "Hora completa en Z1 para recuperar sin acumular fatiga.",
                "execution_notes": ["Potencia < 55% FTP", "Disfruta el paisaje"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Rodaje Z1 completo", "duration_s": 3600,
                 "target": {"zone": "Z1"}, "instructions": "Potencia baja y constante"},
            ],
        },
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 20, "sodium_mg_per_hour": 200},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "est_tss": 30.0,
    },
    {
        "title": "Z1 Post-Race Spin 30min",
        "description": "Rodaje de 30 minutos post-carrera para acelerar la recuperación.",
        "sport_type": "cycling",
        "duration_min": 30,
        "intensity_level": "recovery",
        "tags": ["z1", "recovery", "post_race", "cooldown"],
        "structure": {
            "schema_version": 1,
            "intensity_model": "power_zones",
            "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación post-carrera",
                "description": "Pedaleo suave inmediatamente después de competición.",
                "execution_notes": ["Cadencia libre", "Sin objetivos de potencia"],
                "warnings": ["Hidratación prioritaria"],
            },
            "steps": [
                {"type": "interval", "label": "Spin suave", "duration_s": 1800,
                 "target": {"zone": "Z1"}, "instructions": "Muy suave, sin presión"},
            ],
        },
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 0.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 30, "sodium_mg_per_hour": 400},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.4},
        },
        "est_tss": 12.0,
    },
    {
        "title": "Z1 Easy Endurance 90min",
        "description": "Rodaje largo de recuperación activa. Mantén Z1 durante toda la sesión.",
        "sport_type": "cycling",
        "duration_min": 90,
        "intensity_level": "recovery",
        "tags": ["z1", "recovery", "easy", "endurance"],
        "structure": {
            "schema_version": 1,
            "intensity_model": "power_zones",
            "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación activa prolongada",
                "description": "Sesión larga en Z1 para mantener el volumen sin fatiga.",
                "execution_notes": ["Potencia < 55% FTP todo el tiempo", "Cadencia 85-95 rpm"],
                "warnings": ["Si subes a Z2, reduce la marcha"],
            },
            "steps": [
                {"type": "interval", "label": "Rodaje Z1 largo", "duration_s": 5400,
                 "target": {"zone": "Z1"}, "instructions": "Constante y relajado"},
            ],
        },
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 30, "sodium_mg_per_hour": 300},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "est_tss": 45.0,
    },
    # ── Z2 Base Aerobic (20) ─────────────────────────────────────────────────
    {
        "title": "Z2 Base Ride 60min",
        "description": "Rodaje aeróbico base de 60 minutos. Construye la base de resistencia.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "easy",
        "tags": ["z2", "base", "aerobic", "endurance"],
        "structure": {
            "schema_version": 1,
            "intensity_model": "power_zones",
            "zone_system": "coggan_7",
            "session": {
                "goal": "Desarrollo de la base aeróbica",
                "description": "Sesión continua en Z2 para mejorar la eficiencia metabólica.",
                "execution_notes": ["Potencia 56-75% FTP", "Cadencia 85-95 rpm"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Suave"},
                {"type": "interval", "label": "Bloque Z2", "duration_s": 2700,
                 "target": {"zone": "Z2"}, "instructions": "Constante en Z2"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 300,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 30, "sodium_mg_per_hour": 300},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "est_tss": 55.0,
    },
]

# ── Main logic ────────────────────────────────────────────────────────────────

def main():
    """Seed workout_library table with templates."""
    t0 = time.time()
    total = len(TEMPLATES)
    
    for i, template in enumerate(TEMPLATES, 1):
        title = template["title"]
        print(f"[{i}/{total}] Processing: {title}")
        
        try:
            # Check if exists
            existing = supabase.table("workout_library").select("id").eq("title", title).execute()
            
            if existing.data:
                # Update
                workout_id = existing.data[0]["id"]
                supabase.table("workout_library").update(template).eq("id", workout_id).execute()
                
                # Regenerate embedding
                embedding = rag.generate_template_embedding(template)
                if embedding:
                    supabase.table("workout_library").update({
                        "embedding": embedding,
                        "embedding_status": "ready",
                    }).eq("id", workout_id).execute()
                else:
                    supabase.table("workout_library").update({"embedding_status": "error"}).eq("id", workout_id).execute()
                    seed_logger.error(f"Failed to generate embedding for: {title}")
            else:
                # Insert
                embedding = rag.generate_template_embedding(template)
                template["embedding"] = embedding
                template["embedding_status"] = "ready" if embedding else "error"
                supabase.table("workout_library").insert(template).execute()
                
                if not embedding:
                    seed_logger.error(f"Failed to generate embedding for: {title}")
        
        except Exception as e:
            seed_logger.error(f"Error processing {title}: {e}")
            print(f"  ERROR: {e}")
            continue
    
    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
