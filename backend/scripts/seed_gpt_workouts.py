"""
Seed script para los 35 workouts generados por GPT (+ 1 activación precompetitiva).
Familias: sweetspot (5), threshold (5), vo2max (5), anaerobic (5),
          sprint (5), endurance (5), recovery (5), precomp (1)

Run desde PaceAlyzer_Backend:
    python scripts/seed_gpt_workouts.py
"""
import sys, os, time, logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from db.supabase_client import supabase
from services.rag_service import RAGService

logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "..", "seed_gpt_errors.log"),
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("seed_gpt")
rag = RAGService()

# ─────────────────────────────────────────────────────────────────────────────
# SWEETSPOT (5)
# ─────────────────────────────────────────────────────────────────────────────
SWEETSPOT = [
    {
        "title": "SS-01 | 3x12 Sweet Spot compacto",
        "description": "Sesión de entrada al sweet spot para construir tolerancia al subumbral sin dejar demasiada fatiga residual. La ejecución debe sentirse firme pero controlada, con potencia homogénea y sin deriva excesiva en la última repetición.",
        "sport_type": "cycling",
        "duration_min": 70,
        "intensity_level": "moderate",
        "tags": ["sweetspot", "subumbral", "FTP", "rodillo", "base"],
        "est_tss": 72.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 45.0, "sodium_mg_per_hour": 400.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Construir tolerancia al sweet spot",
                "description": "3 bloques de 12 min a 90% FTP con recuperaciones de 4 min.",
                "execution_notes": ["Potencia homogénea en cada bloque", "No acelerar en el primer bloque"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "3x12 Sweet Spot", "repeat": 3, "steps": [
                    {"type": "interval", "label": "Sweet Spot", "duration_s": 720,
                     "target": {"zone": "Z3", "power": 0.90}, "instructions": "90% FTP, potencia estable"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 240,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 660,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SS-02 | 2x20 Sweet Spot clásico",
        "description": "Plantilla clásica para mejorar la capacidad de sostener potencia estable cerca del umbral durante mucho tiempo. Ideal para subir tiempo de calidad con carga repetible semana a semana.",
        "sport_type": "cycling",
        "duration_min": 75,
        "intensity_level": "hard",
        "tags": ["sweetspot", "resistencia muscular", "FTP", "tempo alto", "indoor"],
        "est_tss": 78.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 50.0, "sodium_mg_per_hour": 400.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Desarrollar resistencia muscular en sweet spot",
                "description": "2 bloques de 20 min a 90% FTP con 5 min de recuperación.",
                "execution_notes": ["Pacing disciplinado", "No superar 92% FTP"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "2x20 Sweet Spot", "repeat": 2, "steps": [
                    {"type": "interval", "label": "Sweet Spot", "duration_s": 1200,
                     "target": {"zone": "Z3", "power": 0.90}, "instructions": "90% FTP constante"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 300,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SS-03 | 4x10 Sweet Spot ágil",
        "description": "Variante más fragmentada para días con menos frescura mental o cuando el deportista tolera mejor bloques cortos. Mantiene el volumen total útil del sweet spot con descansos suficientes para preservar la calidad.",
        "sport_type": "cycling",
        "duration_min": 70,
        "intensity_level": "moderate",
        "tags": ["sweetspot", "time-crunched", "subumbral", "rodillo", "eficiencia"],
        "est_tss": 74.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 45.0, "sodium_mg_per_hour": 400.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Sweet spot fragmentado para días de menor frescura",
                "description": "4 bloques de 10 min a 88-90% FTP con 3 min de recuperación.",
                "execution_notes": ["Bloques cortos, calidad alta", "Recuperaciones activas"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 720,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.72}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "4x10 Sweet Spot", "repeat": 4, "steps": [
                    {"type": "interval", "label": "Sweet Spot", "duration_s": 600,
                     "target": {"zone": "Z3", "power": 0.89}, "instructions": "88-90% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 540,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SS-04 | 3x15 Sweet Spot denso",
        "description": "Sesión más exigente para elevar la densidad del trabajo en la banda alta del sweet spot. Funciona muy bien en bloques de desarrollo de crono o gran fondo.",
        "sport_type": "cycling",
        "duration_min": 85,
        "intensity_level": "hard",
        "tags": ["sweetspot", "densidad", "granfondo", "crono", "TTE"],
        "est_tss": 92.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Elevar densidad de trabajo en sweet spot alto",
                "description": "3 bloques de 15 min a 91-92% FTP con 5 min de recuperación.",
                "execution_notes": ["Requiere frescura", "Potencia en la banda alta del SS"],
                "warnings": ["No ejecutar con TSB muy negativo"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "3x15 Sweet Spot denso", "repeat": 3, "steps": [
                    {"type": "interval", "label": "Sweet Spot alto", "duration_s": 900,
                     "target": {"zone": "Z4", "power": 0.915}, "instructions": "91-92% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 300,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SS-05 | 4x15 Sweet Spot largo",
        "description": "Versión larga para ciclistas con más volumen semanal y buena tolerancia al trabajo sostenido. Desarrolla resistencia muscular, economía de pedaleo y capacidad de sostener esfuerzos prolongados.",
        "sport_type": "cycling",
        "duration_min": 105,
        "intensity_level": "hard",
        "tags": ["sweetspot", "volumen", "granfondo", "diesel", "resistencia muscular"],
        "est_tss": 110.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Resistencia muscular y durabilidad en sweet spot",
                "description": "4 bloques de 15 min a 88-90% FTP con 5 min de recuperación.",
                "execution_notes": ["Solo para atletas con buen volumen base", "Alimentación durante la sesión"],
                "warnings": ["Requiere TSB positivo o neutro"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.72}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "4x15 Sweet Spot", "repeat": 4, "steps": [
                    {"type": "interval", "label": "Sweet Spot", "duration_s": 900,
                     "target": {"zone": "Z3", "power": 0.89}, "instructions": "88-90% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 300,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# THRESHOLD / FTP (5)
# ─────────────────────────────────────────────────────────────────────────────
THRESHOLD = [
    {
        "title": "TH-01 | 2x10 FTP Express",
        "description": "Plantilla corta para semanas de poco tiempo o para introducir trabajo umbral sin comprometer el resto del microciclo. Buena opción para deportistas con TSB neutro que necesitan mantener el estímulo de FTP.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "hard",
        "tags": ["FTP", "threshold", "express", "time-crunched", "mantenimiento"],
        "est_tss": 62.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 50.0, "sodium_mg_per_hour": 400.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Mantener estímulo de FTP en sesión corta",
                "description": "2 bloques de 10 min a 98-100% FTP con 5 min de recuperación.",
                "execution_notes": ["Pacing disciplinado", "No superar FTP en el primer bloque"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 2x1min a 90-95%"},
                {"type": "repeat", "label": "2x10 FTP", "repeat": 2, "steps": [
                    {"type": "interval", "label": "Umbral", "duration_s": 600,
                     "target": {"zone": "Z4", "power": 0.99}, "instructions": "98-100% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 300,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Tempo suave", "duration_s": 600,
                 "target": {"zone": "Z2", "power": 0.67}, "instructions": "65-70% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "TH-02 | 3x8 FTP compacto",
        "description": "Formato que permite acumular trabajo de calidad con sensación algo más llevadera que un 2x20. Especialmente útil para atletas que responden mejor a repeticiones más cortas pero quieren permanecer claramente en Z4.",
        "sport_type": "cycling",
        "duration_min": 65,
        "intensity_level": "hard",
        "tags": ["FTP", "threshold", "cruise intervals", "rodillo", "compact"],
        "est_tss": 71.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 50.0, "sodium_mg_per_hour": 400.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Trabajo de umbral con bloques cortos",
                "description": "3 bloques de 8 min a 100-102% FTP con 3 min de recuperación.",
                "execution_notes": ["Recuperaciones de 3 min para mantener calidad", "Potencia constante"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1080,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 3x45s a 90-95%"},
                {"type": "repeat", "label": "3x8 FTP", "repeat": 3, "steps": [
                    {"type": "interval", "label": "Umbral", "duration_s": 480,
                     "target": {"zone": "Z4", "power": 1.01}, "instructions": "100-102% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 1140,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "TH-03 | 4x8 FTP sostenido",
        "description": "Sesión muy eficiente para elevar la tolerancia al umbral. La clave es no sobrepasar la potencia objetivo en la primera mitad para no deteriorar la cuarta serie.",
        "sport_type": "cycling",
        "duration_min": 70,
        "intensity_level": "hard",
        "tags": ["FTP", "threshold", "pacing", "TT", "control"],
        "est_tss": 83.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Elevar tolerancia al umbral con 4 series",
                "description": "4 bloques de 8 min a 99-102% FTP con 3 min de recuperación.",
                "execution_notes": ["Pacing muy disciplinado", "La 4ª serie debe ser igual que la 1ª"],
                "warnings": ["Requiere TSB positivo o neutro"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 960,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "4x8 FTP", "repeat": 4, "steps": [
                    {"type": "interval", "label": "Umbral", "duration_s": 480,
                     "target": {"zone": "Z4", "power": 1.005}, "instructions": "99-102% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 960,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "TH-04 | 3x12 Cruise FTP",
        "description": "Variante cruise para ampliar tiempo útil en umbral sin llegar a bloques de 20 minutos. Buena plantilla de desarrollo cuando el atleta ya tolera bien el sweet spot y necesita más especificidad de FTP.",
        "sport_type": "cycling",
        "duration_min": 90,
        "intensity_level": "very_hard",
        "tags": ["FTP", "threshold", "cruise", "desarrollo", "TTE"],
        "est_tss": 102.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Ampliar tiempo en umbral con cruise intervals",
                "description": "3 bloques de 12 min a 98-100% FTP con 4 min de recuperación, más 16 min de tempo.",
                "execution_notes": ["Potencia estable en cada bloque", "El bloque de tempo es parte del trabajo"],
                "warnings": ["Solo para atletas frescos"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1080,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "3x12 FTP", "repeat": 3, "steps": [
                    {"type": "interval", "label": "Umbral", "duration_s": 720,
                     "target": {"zone": "Z4", "power": 0.99}, "instructions": "98-100% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 240,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Tempo continuo", "duration_s": 960,
                 "target": {"zone": "Z2", "power": 0.67}, "instructions": "65-70% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 720,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "TH-05 | 2x20 FTP largo",
        "description": "Sesión de referencia para trabajar el motor de crono: mucha concentración, potencia estable y cadencia constante. Debe ejecutarse con pacing muy disciplinado, evitando picos por encima de FTP.",
        "sport_type": "cycling",
        "duration_min": 100,
        "intensity_level": "very_hard",
        "tags": ["FTP", "contrarreloj", "threshold", "largo", "TTE"],
        "est_tss": 114.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Desarrollar motor de crono con 2x20 FTP",
                "description": "2 bloques de 20 min a 98-100% FTP con 8 min de recuperación, más 17 min de tempo.",
                "execution_notes": ["Pacing muy disciplinado", "Cadencia constante 85-90 rpm"],
                "warnings": ["Solo para atletas muy frescos", "No superar FTP en ningún momento"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1200,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo"},
                {"type": "repeat", "label": "2x20 FTP", "repeat": 2, "steps": [
                    {"type": "interval", "label": "Umbral", "duration_s": 1200,
                     "target": {"zone": "Z4", "power": 0.99}, "instructions": "98-100% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 480,
                     "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                ]},
                {"type": "interval", "label": "Tempo continuo", "duration_s": 1020,
                 "target": {"zone": "Z2", "power": 0.67}, "instructions": "65-70% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# VO2MAX (5)
# ─────────────────────────────────────────────────────────────────────────────
VO2MAX = [
    {
        "title": "VO2-01 | 5x3 VO2max entrada",
        "description": "Introducción controlada al trabajo de VO2max, ideal para iniciar un bloque o para atletas que aún no toleran bien repeticiones largas. La prioridad es que todas las series sean nítidas y similares.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "hard",
        "tags": ["VO2max", "3min", "entrada", "punch", "rodillo"],
        "est_tss": 71.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Introducción al trabajo de VO2max",
                "description": "5 series de 3 min a 116-118% FTP con 3 min de recuperación.",
                "execution_notes": ["Todas las series deben ser similares", "No all-out en la primera"],
                "warnings": ["Solo con TSB positivo"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 3x1min a 95-100%"},
                {"type": "repeat", "label": "5x3 VO2max", "repeat": 5, "steps": [
                    {"type": "interval", "label": "VO2max", "duration_s": 180,
                     "target": {"zone": "Z5", "power": 1.17}, "instructions": "116-118% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 1080,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "VO2-02 | 4x4 VO2max clásico",
        "description": "Plantilla clásica para elevar techo aeróbico. En deportistas bien frescos es una de las formas más limpias de trabajar VO2max sin grandes complejidades tácticas.",
        "sport_type": "cycling",
        "duration_min": 65,
        "intensity_level": "hard",
        "tags": ["VO2max", "4min", "clásico", "aeróbico máximo", "calidad"],
        "est_tss": 76.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Elevar techo aeróbico con 4x4",
                "description": "4 series de 4 min a 112-115% FTP con 4 min de recuperación.",
                "execution_notes": ["Recuperaciones 1:1", "Potencia constante en cada serie"],
                "warnings": ["Requiere TSB positivo"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1080,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 3x1min a 100%"},
                {"type": "repeat", "label": "4x4 VO2max", "repeat": 4, "steps": [
                    {"type": "interval", "label": "VO2max", "duration_s": 240,
                     "target": {"zone": "Z5", "power": 1.135}, "instructions": "112-115% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 240,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 1140,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "VO2-03 | 4x5 VO2max sostenido",
        "description": "Versión más exigente para aumentar el tiempo útil cerca del consumo máximo de oxígeno. Exige pacing muy fino: si se sobrepasa el rango pronto, la tercera y cuarta repetición pierden calidad.",
        "sport_type": "cycling",
        "duration_min": 75,
        "intensity_level": "very_hard",
        "tags": ["VO2max", "5min", "capacidad aeróbica", "subida", "duro"],
        "est_tss": 87.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Aumentar tiempo útil en VO2max",
                "description": "4 series de 5 min a 108-112% FTP con 5 min de recuperación.",
                "execution_notes": ["Pacing muy fino", "No empezar demasiado fuerte"],
                "warnings": ["Solo para atletas muy frescos"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1200,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 3x1min a 95-100%"},
                {"type": "repeat", "label": "4x5 VO2max", "repeat": 4, "steps": [
                    {"type": "interval", "label": "VO2max", "duration_s": 300,
                     "target": {"zone": "Z5", "power": 1.10}, "instructions": "108-112% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 300,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 1200,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "VO2-04 | 3x6 VO2max largo",
        "description": "VO2max más maduro: menos explosivo, más cercano a un esfuerzo de subida larga o persecución sostenida. Funciona muy bien en atletas con buena economía y buen control de ritmo.",
        "sport_type": "cycling",
        "duration_min": 75,
        "intensity_level": "very_hard",
        "tags": ["VO2max", "6min", "climbing", "aeróbico", "build"],
        "est_tss": 83.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "VO2max sostenido tipo subida larga",
                "description": "3 series de 6 min a 106-110% FTP con 5 min de recuperación, más 12 min de tempo.",
                "execution_notes": ["Control de ritmo esencial", "Cadencia 85-90 rpm"],
                "warnings": ["Solo para atletas frescos con buena base"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1200,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 2x90s a 95-100%"},
                {"type": "repeat", "label": "3x6 VO2max", "repeat": 3, "steps": [
                    {"type": "interval", "label": "VO2max", "duration_s": 360,
                     "target": {"zone": "Z5", "power": 1.08}, "instructions": "106-110% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 300,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Tempo continuo", "duration_s": 720,
                 "target": {"zone": "Z2", "power": 0.67}, "instructions": "65-70% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "VO2-05 | Escalera 3-4-5-4-3 VO2max",
        "description": "Escalera para mantener foco mental y variar la percepción del esfuerzo sin salir del mismo objetivo fisiológico. La idea es empujar con control, manteniendo la última repetición tan sólida como la primera.",
        "sport_type": "cycling",
        "duration_min": 90,
        "intensity_level": "very_hard",
        "tags": ["VO2max", "escalera", "aeróbico máximo", "variado", "resistente"],
        "est_tss": 99.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "VO2max en escalera para variedad mental",
                "description": "Escalera 3-4-5-4-3 min a 110-115% FTP con 3 min de recuperación entre cada bloque.",
                "execution_notes": ["Misma potencia en todos los bloques", "La escalera es mental, no de intensidad"],
                "warnings": ["Solo para atletas muy frescos"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1200,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 3x1min a 95-100%"},
                {"type": "interval", "label": "VO2max 3min", "duration_s": 180,
                 "target": {"zone": "Z5", "power": 1.125}, "instructions": "110-115% FTP"},
                {"type": "interval", "label": "Recuperación", "duration_s": 180,
                 "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                {"type": "interval", "label": "VO2max 4min", "duration_s": 240,
                 "target": {"zone": "Z5", "power": 1.125}, "instructions": "110-115% FTP"},
                {"type": "interval", "label": "Recuperación", "duration_s": 180,
                 "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                {"type": "interval", "label": "VO2max 5min", "duration_s": 300,
                 "target": {"zone": "Z5", "power": 1.125}, "instructions": "110-115% FTP"},
                {"type": "interval", "label": "Recuperación", "duration_s": 180,
                 "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                {"type": "interval", "label": "VO2max 4min", "duration_s": 240,
                 "target": {"zone": "Z5", "power": 1.125}, "instructions": "110-115% FTP"},
                {"type": "interval", "label": "Recuperación", "duration_s": 180,
                 "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                {"type": "interval", "label": "VO2max 3min", "duration_s": 180,
                 "target": {"zone": "Z5", "power": 1.125}, "instructions": "110-115% FTP"},
                {"type": "interval", "label": "Tempo continuo", "duration_s": 1440,
                 "target": {"zone": "Z2", "power": 0.67}, "instructions": "65-70% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# ANAERÓBICO / FRC (5)
# ─────────────────────────────────────────────────────────────────────────────
ANAEROBIC = [
    {
        "title": "AN-01 | 10x1' FRC repetible",
        "description": "Sesión orientada a mejorar la capacidad de repetir aceleraciones y cambios de ritmo por encima de FTP sin colapsar tras las primeras series. Cada minuto debe ser duro pero controlado.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "hard",
        "tags": ["FRC", "anaeróbico", "1min", "repetibilidad", "ataques"],
        "est_tss": 72.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Mejorar repetibilidad de esfuerzos anaeróbicos",
                "description": "10 series de 1 min a 130-135% FTP con 2 min de recuperación.",
                "execution_notes": ["No all-out en las primeras series", "Recuperaciones completas"],
                "warnings": ["Solo con TSB positivo"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 3x30s a 95-100%"},
                {"type": "interval", "label": "Activación", "duration_s": 120,
                 "target": {"zone": "Z2", "power": 0.60}, "instructions": "Suave antes del bloque"},
                {"type": "repeat", "label": "10x1min FRC", "repeat": 10, "steps": [
                    {"type": "interval", "label": "Anaeróbico", "duration_s": 60,
                     "target": {"zone": "Z6", "power": 1.325}, "instructions": "130-135% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 120,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "AN-02 | 8x90\" punch largo",
        "description": "Punto intermedio entre potencia anaeróbica y resistencia al lactato. Funciona bien para corredores que necesitan una respuesta fuerte en repechos, cambios de ritmo o persecuciones cortas.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "hard",
        "tags": ["FRC", "anaeróbico", "90s", "punch", "colinas"],
        "est_tss": 74.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Potencia anaeróbica en esfuerzos de 90 segundos",
                "description": "8 series de 90s a 125-128% FTP con 2:30 de recuperación.",
                "execution_notes": ["Potencia constante en cada serie", "Recuperaciones completas"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 3x30s a 100%"},
                {"type": "repeat", "label": "8x90s FRC", "repeat": 8, "steps": [
                    {"type": "interval", "label": "Anaeróbico", "duration_s": 90,
                     "target": {"zone": "Z6", "power": 1.265}, "instructions": "125-128% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 150,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Tempo suave", "duration_s": 600,
                 "target": {"zone": "Z2", "power": 0.66}, "instructions": "65-68% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 300,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "AN-03 | 6x2' FRC largo",
        "description": "Versión robusta orientada a producir mucho trabajo útil por encima de FTP con fuerte participación glucolítica. Requiere frescura y capacidad de sufrir sin romper la técnica de pedaleo.",
        "sport_type": "cycling",
        "duration_min": 70,
        "intensity_level": "very_hard",
        "tags": ["FRC", "anaeróbico", "2min", "tolerancia lactato", "race-like"],
        "est_tss": 80.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Tolerancia al lactato con esfuerzos de 2 minutos",
                "description": "6 series de 2 min a 121-125% FTP con 3 min de recuperación.",
                "execution_notes": ["Técnica de pedaleo constante", "No romper en las últimas series"],
                "warnings": ["Solo para atletas frescos"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1080,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 2x1min a 100%"},
                {"type": "repeat", "label": "6x2min FRC", "repeat": 6, "steps": [
                    {"type": "interval", "label": "Anaeróbico", "duration_s": 120,
                     "target": {"zone": "Z6", "power": 1.23}, "instructions": "121-125% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Tempo suave", "duration_s": 600,
                 "target": {"zone": "Z2", "power": 0.67}, "instructions": "65-70% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "AN-04 | 2x6x40\" microataques",
        "description": "Reproduce el patrón de aceleraciones repetidas de una carrera nerviosa o subida irregular. El objetivo es volver a producir potencia alta una y otra vez, no solo hacer un primer bloque brillante.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "very_hard",
        "tags": ["microburst", "FRC", "anaeróbico", "criterium", "repetición"],
        "est_tss": 77.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Repetibilidad de microataques tipo carrera",
                "description": "2 sets de 6x40s a 138-145% FTP con 1:20 de recuperación y 5 min entre sets.",
                "execution_notes": ["Calidad constante en todos los microataques", "El segundo set debe ser igual al primero"],
                "warnings": ["Solo para atletas frescos"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 4x20s a 100-105%"},
                {"type": "repeat", "label": "Set 1: 6x40s", "repeat": 6, "steps": [
                    {"type": "interval", "label": "Microataque", "duration_s": 40,
                     "target": {"zone": "Z6", "power": 1.415}, "instructions": "138-145% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 80,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Recuperación entre sets", "duration_s": 300,
                 "target": {"zone": "Z1", "power": 0.52}, "instructions": "Suave"},
                {"type": "repeat", "label": "Set 2: 6x40s", "repeat": 6, "steps": [
                    {"type": "interval", "label": "Microataque", "duration_s": 40,
                     "target": {"zone": "Z6", "power": 1.415}, "instructions": "138-145% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 80,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 720,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "AN-05 | 2x8x30\" anaeróbico corto",
        "description": "Sesión rápida y agresiva para mejorar la respuesta a ataques cortos, arrancadas y latigazos de carrera. Máxima firmeza sin descontrol, dejando sensación de poder empujar en las últimas repeticiones.",
        "sport_type": "cycling",
        "duration_min": 65,
        "intensity_level": "very_hard",
        "tags": ["anaeróbico", "30s", "FRC", "sprint-resistencia", "race prep"],
        "est_tss": 86.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Respuesta a ataques cortos y arrancadas",
                "description": "2 sets de 8x30s a 145-150% FTP con 1 min de recuperación y 5 min entre sets.",
                "execution_notes": ["Explosividad controlada", "Recuperaciones completas"],
                "warnings": ["Solo para atletas frescos"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1080,
                 "target": {"zone": "Z2", "power_low": 0.55, "power_high": 0.75}, "instructions": "Progresivo con 4x20s a 100-105%"},
                {"type": "repeat", "label": "Set 1: 8x30s", "repeat": 8, "steps": [
                    {"type": "interval", "label": "Anaeróbico", "duration_s": 30,
                     "target": {"zone": "Z6", "power": 1.475}, "instructions": "145-150% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 60,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Recuperación entre sets", "duration_s": 300,
                 "target": {"zone": "Z1", "power": 0.52}, "instructions": "Suave"},
                {"type": "repeat", "label": "Set 2: 8x30s", "repeat": 8, "steps": [
                    {"type": "interval", "label": "Anaeróbico", "duration_s": 30,
                     "target": {"zone": "Z6", "power": 1.475}, "instructions": "145-150% FTP"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 60,
                     "target": {"zone": "Z1", "power": 0.52}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Tempo suave", "duration_s": 600,
                 "target": {"zone": "Z2", "power": 0.66}, "instructions": "65-68% FTP"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# SPRINT / NEUROMUSCULAR (5)
# ─────────────────────────────────────────────────────────────────────────────
SPRINT = [
    {
        "title": "SP-01 | 8x10\" sprints lanzados",
        "description": "Sprint rodado para trabajar pico de potencia sin el coste técnico de una arrancada desde parado. Ideal para priorizar velocidad de piernas, aceleración limpia y coordinación neuromuscular.",
        "sport_type": "cycling",
        "duration_min": 50,
        "intensity_level": "hard",
        "tags": ["sprint", "neuromuscular", "lanzado", "peak power", "velocidad"],
        "est_tss": 50.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 30.0, "sodium_mg_per_hour": 300.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Desarrollar pico de potencia neuromuscular",
                "description": "8 sprints de 10s a >160% FTP con 3 min de recuperación completa.",
                "execution_notes": ["Intención máxima en cada sprint", "Recuperaciones completas para mantener calidad"],
                "warnings": ["Detener si la potencia cae más de un 5%"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1200,
                 "target": {"zone": "Z2", "power_low": 0.50, "power_high": 0.70}, "instructions": "Progresivo con 3x6s a >150%"},
                {"type": "repeat", "label": "8x10s sprints", "repeat": 8, "steps": [
                    {"type": "interval", "label": "Sprint", "duration_s": 10,
                     "target": {"zone": "Z7", "power": 1.70}, "instructions": "160-180% FTP, intención máxima"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 480,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SP-02 | 10x12\" sprints fuerza",
        "description": "Variante orientada a producir mucha fuerza inicial sobre el pedal, útil para salidas de curva, arrancadas y llegadas explosivas. Prioridad en técnica y estabilidad del tronco.",
        "sport_type": "cycling",
        "duration_min": 55,
        "intensity_level": "hard",
        "tags": ["sprint", "fuerza", "salida", "neuromuscular", "aceleración"],
        "est_tss": 56.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 30.0, "sodium_mg_per_hour": 300.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Fuerza inicial y explosividad en arrancadas",
                "description": "10 sprints de 12s a 170-190% FTP con 3 min de recuperación.",
                "execution_notes": ["Empujar con técnica y estabilidad", "No tirar de espalda"],
                "warnings": ["Detener si la potencia cae más de un 5%"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1200,
                 "target": {"zone": "Z2", "power_low": 0.50, "power_high": 0.70}, "instructions": "Progresivo con 3x8s a >150%"},
                {"type": "repeat", "label": "10x12s sprints", "repeat": 10, "steps": [
                    {"type": "interval", "label": "Sprint fuerza", "duration_s": 12,
                     "target": {"zone": "Z7", "power": 1.80}, "instructions": "170-190% FTP, fuerza máxima"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 360,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SP-03 | 12x8\" sprints cuesta",
        "description": "La ligera pendiente permite aplicar más par y obliga a una aceleración más de carrera. Gran plantilla para ciclistas que responden mejor cuando el sprint se apoya en torque y no solo en cadencia extrema.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "hard",
        "tags": ["sprint", "cuesta", "torque", "neuromuscular", "explosividad"],
        "est_tss": 64.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 30.0, "sodium_mg_per_hour": 300.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Potencia máxima con torque en cuesta",
                "description": "12 sprints de 8s a 180-220% FTP en pendiente con 3 min de recuperación.",
                "execution_notes": ["Buscar pendiente del 4-6%", "Intención máxima desde el primer pedaleo"],
                "warnings": ["Detener si la potencia cae más de un 5%"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1080,
                 "target": {"zone": "Z2", "power_low": 0.50, "power_high": 0.70}, "instructions": "Progresivo con 3x6s a >150%"},
                {"type": "repeat", "label": "12x8s sprints cuesta", "repeat": 12, "steps": [
                    {"type": "interval", "label": "Sprint cuesta", "duration_s": 8,
                     "target": {"zone": "Z7", "power": 2.00}, "instructions": "180-220% FTP, torque máximo"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 420,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SP-04 | 2x6x6\" alta cadencia",
        "description": "Trabajo centrado en rapidez de reclutamiento y coordinación a alta velocidad de piernas, con carga metabólica comparativamente baja. Útil para mantener activación neuromuscular en semanas de menor carga.",
        "sport_type": "cycling",
        "duration_min": 45,
        "intensity_level": "moderate",
        "tags": ["sprint", "cadencia", "activación", "neuromuscular", "mantenimiento"],
        "est_tss": 37.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 20.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Activación neuromuscular con alta cadencia",
                "description": "2 sets de 6x6s a >150% FTP con 1:30 de recuperación y 5 min entre sets.",
                "execution_notes": ["Desarrollo ligero", "Cadencia muy alta", "Carga metabólica baja"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z2", "power_low": 0.50, "power_high": 0.68}, "instructions": "Progresivo con 4x6s a >150%"},
                {"type": "repeat", "label": "Set 1: 6x6s", "repeat": 6, "steps": [
                    {"type": "interval", "label": "Sprint cadencia", "duration_s": 6,
                     "target": {"zone": "Z7", "power": 1.60}, "instructions": ">150% FTP, cadencia máxima"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 90,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Recuperación entre sets", "duration_s": 300,
                 "target": {"zone": "Z1", "power": 0.47}, "instructions": "Suave"},
                {"type": "repeat", "label": "Set 2: 6x6s", "repeat": 6, "steps": [
                    {"type": "interval", "label": "Sprint cadencia", "duration_s": 6,
                     "target": {"zone": "Z7", "power": 1.60}, "instructions": ">150% FTP, cadencia máxima"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 90,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 480,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "SP-05 | 3x3x12\" sprints con fondo",
        "description": "Plantilla mixta para practicar sprints de calidad después de una carga aeróbica suave. Útil en preparación de criterios, gravel competitivo o ruta con final nervioso.",
        "sport_type": "cycling",
        "duration_min": 75,
        "intensity_level": "hard",
        "tags": ["sprint", "final de carrera", "neuromuscular", "ruta", "velocidad final"],
        "est_tss": 67.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
            "during": {"carbs_g_per_hour": 40.0, "sodium_mg_per_hour": 400.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Sprints de calidad después de carga aeróbica",
                "description": "15 min de fondo suave, luego 3 sets de 3x12s a 170-200% FTP con 3 min de recuperación.",
                "execution_notes": ["Si la técnica cae, cortar la sesión", "El fondo previo simula la fatiga de carrera"],
                "warnings": ["No ejecutar si hay fatiga muscular acumulada"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 1200,
                 "target": {"zone": "Z2", "power_low": 0.50, "power_high": 0.70}, "instructions": "Progresivo"},
                {"type": "interval", "label": "Fondo previo", "duration_s": 900,
                 "target": {"zone": "Z2", "power": 0.67}, "instructions": "65-70% FTP"},
                {"type": "repeat", "label": "3 sets de 3x12s", "repeat": 3, "steps": [
                    {"type": "interval", "label": "Sprint", "duration_s": 12,
                     "target": {"zone": "Z7", "power": 1.85}, "instructions": "170-200% FTP, intención máxima"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 180,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# ENDURANCE / BASE (5)
# ─────────────────────────────────────────────────────────────────────────────
ENDURANCE = [
    {
        "title": "EB-01 | Fondo corto Z2 60min",
        "description": "Sesión simple para acumular volumen aeróbico con bajo coste fisiológico. Debe sentirse muy sostenible, con respiración estable y sensación de que se podría continuar bastante más tiempo.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "easy",
        "tags": ["base", "Z2", "fondo corto", "aeróbico", "mantenimiento"],
        "est_tss": 35.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 20.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Acumular volumen aeróbico base",
                "description": "40 min continuos a 60-65% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Potencia constante", "Cadencia 85-95 rpm"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 600,
                 "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                {"type": "interval", "label": "Fondo Z2", "duration_s": 2400,
                 "target": {"zone": "Z2", "power": 0.625}, "instructions": "60-65% FTP constante"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "EB-02 | Fondo medio Z2 90min",
        "description": "Plantilla base para semanas generales de construcción aeróbica. Sirve para consolidar economía, estabilidad cardíaca y tolerancia al sillín sin meter tensión metabólica alta.",
        "sport_type": "cycling",
        "duration_min": 90,
        "intensity_level": "easy",
        "tags": ["base", "Z2", "aeróbico", "endurance", "semana tipo"],
        "est_tss": 59.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 30.0, "sodium_mg_per_hour": 300.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Construcción aeróbica base",
                "description": "70 min continuos a 62-67% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Potencia constante", "Sin deriva de pulso"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 600,
                 "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                {"type": "interval", "label": "Fondo Z2", "duration_s": 4200,
                 "target": {"zone": "Z2", "power": 0.645}, "instructions": "62-67% FTP constante"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "EB-03 | Fondo clásico Z2 120min",
        "description": "Dos horas de trabajo aeróbico estable para mejorar durabilidad y control de esfuerzo. La pauta de ejecución es potencia pareja, alimentación adecuada y mínima deriva de pulso.",
        "sport_type": "cycling",
        "duration_min": 120,
        "intensity_level": "moderate",
        "tags": ["base", "Z2", "2h", "durabilidad", "fondo"],
        "est_tss": 87.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 45.0, "sodium_mg_per_hour": 400.0},
            "post": {"carbs_g_per_kg": 1.2, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Durabilidad aeróbica de 2 horas",
                "description": "100 min continuos a 65-70% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Alimentación cada 45 min", "Potencia pareja sin subidas"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 600,
                 "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                {"type": "interval", "label": "Fondo Z2", "duration_s": 6000,
                 "target": {"zone": "Z2", "power": 0.675}, "instructions": "65-70% FTP constante"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "EB-04 | Fondo largo Z2 150min",
        "description": "Plantilla para atletas de gran fondo, XC maratón, gravel o ruta con mayor disponibilidad de horas. Lo importante es mantener la paciencia y no subirse al sweet spot por sensación de facilidad.",
        "sport_type": "cycling",
        "duration_min": 150,
        "intensity_level": "moderate",
        "tags": ["base", "Z2", "granfondo", "gravel", "volumen"],
        "est_tss": 114.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Volumen aeróbico largo para gran fondo",
                "description": "120 min continuos a 66-70% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Alimentación cada 40 min", "No subir a Z3 aunque se sienta fácil"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                {"type": "interval", "label": "Fondo Z2", "duration_s": 7200,
                 "target": {"zone": "Z2", "power": 0.68}, "instructions": "66-70% FTP constante"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
    {
        "title": "EB-05 | Tirada reina Z2 180min",
        "description": "La sesión reina de resistencia general. Reservarla para ciclistas con volumen semanal suficiente. Busca durabilidad, economía de combustible y capacidad de sostener un día largo.",
        "sport_type": "cycling",
        "duration_min": 180,
        "intensity_level": "moderate",
        "tags": ["base", "Z2", "tirada larga", "resistencia", "durabilidad"],
        "est_tss": 146.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 2.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 60.0, "sodium_mg_per_hour": 500.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.4},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Durabilidad máxima en Z2",
                "description": "150 min continuos a 68-72% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Alimentación cada 35-40 min", "Hidratación constante"],
                "warnings": ["Solo para atletas con base sólida y volumen semanal alto"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 900,
                 "target": {"zone": "Z1", "power": 0.57}, "instructions": "Suave"},
                {"type": "interval", "label": "Fondo Z2", "duration_s": 9000,
                 "target": {"zone": "Z2", "power": 0.70}, "instructions": "68-72% FTP constante"},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 900,
                 "target": {"zone": "Z1"}, "instructions": "Reduce gradualmente"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# RECOVERY (5)
# ─────────────────────────────────────────────────────────────────────────────
RECOVERY = [
    {
        "title": "RC-01 | Soltar piernas 30min",
        "description": "Recuperación activa muy sencilla para el día posterior a una sesión dura o a una carrera. El objetivo es favorecer circulación y movilidad sin añadir ninguna demanda real al sistema.",
        "sport_type": "cycling",
        "duration_min": 30,
        "intensity_level": "recovery",
        "tags": ["recovery", "soltura", "flush", "Z1", "post-intenso"],
        "est_tss": 9.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 0.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 0.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación activa post-esfuerzo",
                "description": "20 min continuos a 40-45% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Sin presión en los pedales", "Cadencia libre"],
                "warnings": ["No superar Z1 en ningún momento"],
            },
            "steps": [
                {"type": "interval", "label": "Inicio suave", "duration_s": 300,
                 "target": {"zone": "Z1", "power": 0.40}, "instructions": "38-42% FTP"},
                {"type": "interval", "label": "Recuperación activa", "duration_s": 1200,
                 "target": {"zone": "Z1", "power": 0.425}, "instructions": "40-45% FTP, muy suave"},
                {"type": "interval", "label": "Cierre", "duration_s": 300,
                 "target": {"zone": "Z1", "power": 0.375}, "instructions": "35-40% FTP"},
            ],
        },
    },
    {
        "title": "RC-02 | Recuperación fluida 35min",
        "description": "Plantilla útil cuando el ciclista quiere rodar un poco más sin salir en ningún momento del dominio de recuperación. La sensación debe ser casi de paseo, con conversación totalmente fácil.",
        "sport_type": "cycling",
        "duration_min": 35,
        "intensity_level": "recovery",
        "tags": ["recovery", "Z1", "regenerativo", "easy spin", "descarga"],
        "est_tss": 12.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 0.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 0.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación regenerativa",
                "description": "25 min continuos a 42-47% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Conversación fácil en todo momento", "Sin objetivos de potencia"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Inicio suave", "duration_s": 300,
                 "target": {"zone": "Z1", "power": 0.40}, "instructions": "38-42% FTP"},
                {"type": "interval", "label": "Recuperación", "duration_s": 1500,
                 "target": {"zone": "Z1", "power": 0.445}, "instructions": "42-47% FTP"},
                {"type": "interval", "label": "Cierre", "duration_s": 300,
                 "target": {"zone": "Z1", "power": 0.375}, "instructions": "35-40% FTP"},
            ],
        },
    },
    {
        "title": "RC-03 | Recuperación con cadencia 45min",
        "description": "Mantiene el carácter regenerativo pero añade pequeños cambios de cadencia para soltar piernas y mejorar sensación de pedaleo. La potencia debe seguir siendo claramente baja en todo momento.",
        "sport_type": "cycling",
        "duration_min": 45,
        "intensity_level": "recovery",
        "tags": ["recovery", "cadencia", "regenerativo", "Z1", "técnica suave"],
        "est_tss": 17.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 0.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 0.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación con trabajo de cadencia suave",
                "description": "29 min a 45-50% FTP con 5 bloques de 1 min a cadencia alta.",
                "execution_notes": ["Potencia baja siempre", "Los bloques de cadencia son técnicos, no de intensidad"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 480,
                 "target": {"zone": "Z1", "power": 0.425}, "instructions": "40-45% FTP"},
                {"type": "repeat", "label": "5x cadencia alta", "repeat": 5, "steps": [
                    {"type": "interval", "label": "Cadencia alta", "duration_s": 60,
                     "target": {"zone": "Z1", "power": 0.51}, "instructions": "50-52% FTP, cadencia 100+ rpm"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 120,
                     "target": {"zone": "Z1", "power": 0.435}, "instructions": "42-45% FTP"},
                ]},
                {"type": "interval", "label": "Cierre", "duration_s": 480,
                 "target": {"zone": "Z1", "power": 0.375}, "instructions": "35-40% FTP"},
            ],
        },
    },
    {
        "title": "RC-04 | Reset aeróbico 50min",
        "description": "Sesión algo más larga para días de cansancio general en los que aun así conviene moverse. Apropiada tras acumulación de carga o para reactivar después de viaje o rigidez muscular.",
        "sport_type": "cycling",
        "duration_min": 50,
        "intensity_level": "recovery",
        "tags": ["recovery", "reset", "Z1", "soltura", "movilidad"],
        "est_tss": 21.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 0.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 0.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Reset aeróbico para días de cansancio general",
                "description": "30 min continuos a 45-50% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Sin objetivos de potencia", "Moverse para recuperar"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 600,
                 "target": {"zone": "Z1", "power": 0.425}, "instructions": "40-45% FTP"},
                {"type": "interval", "label": "Reset aeróbico", "duration_s": 1800,
                 "target": {"zone": "Z1", "power": 0.475}, "instructions": "45-50% FTP"},
                {"type": "interval", "label": "Cierre", "duration_s": 600,
                 "target": {"zone": "Z1", "power": 0.375}, "instructions": "35-40% FTP"},
            ],
        },
    },
    {
        "title": "RC-05 | Paseo regenerativo 60min",
        "description": "Recuperación larga pero todavía muy fácil, útil en bloques de bastante volumen donde un descanso total no siempre es necesario. Debe terminar con sensación de frescura, no de haber entrenado.",
        "sport_type": "cycling",
        "duration_min": 60,
        "intensity_level": "recovery",
        "tags": ["recovery", "regenerativo", "Z1", "paseo", "descarga"],
        "est_tss": 23.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 0.5, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 0.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.3},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Recuperación larga y regenerativa",
                "description": "40 min continuos a 45-48% FTP con calentamiento y vuelta a la calma.",
                "execution_notes": ["Terminar más fresco que al empezar", "Sin presión"],
                "warnings": [],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento", "duration_s": 600,
                 "target": {"zone": "Z1", "power": 0.42}, "instructions": "40-44% FTP"},
                {"type": "interval", "label": "Paseo regenerativo", "duration_s": 2400,
                 "target": {"zone": "Z1", "power": 0.465}, "instructions": "45-48% FTP"},
                {"type": "interval", "label": "Cierre", "duration_s": 600,
                 "target": {"zone": "Z1", "power": 0.375}, "instructions": "35-40% FTP"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# ACTIVACIÓN PRECOMPETITIVA (1) — gap identificado en los logs
# ─────────────────────────────────────────────────────────────────────────────
PRECOMP = [
    {
        "title": "PC-01 | Activación precompetitiva 40min",
        "description": "Sesión de activación para el día antes o la mañana de una competición. Mantiene las piernas activas, activa el sistema neuromuscular con sprints cortos y no genera fatiga residual.",
        "sport_type": "cycling",
        "duration_min": 40,
        "intensity_level": "easy",
        "tags": ["activación", "precompetitivo", "race day", "neuromuscular", "taper"],
        "est_tss": 28.0,
        "nutrition_template": {
            "pre": {"carbs_g_per_kg": 1.0, "protein_g_per_kg": 0.0},
            "during": {"carbs_g_per_hour": 20.0, "sodium_mg_per_hour": 200.0},
            "post": {"carbs_g_per_kg": 1.5, "protein_g_per_kg": 0.2},
        },
        "structure": {
            "schema_version": 1, "intensity_model": "power_zones", "zone_system": "coggan_7",
            "session": {
                "goal": "Activar piernas sin generar fatiga antes de competición",
                "description": "Rodaje suave con 3 sprints cortos de activación neuromuscular y 2 bloques de 1 min a umbral.",
                "execution_notes": ["Los sprints son de activación, no de esfuerzo máximo", "Terminar sintiéndose fresco"],
                "warnings": ["No ejecutar si hay fatiga muscular acumulada"],
            },
            "steps": [
                {"type": "interval", "label": "Calentamiento suave", "duration_s": 900,
                 "target": {"zone": "Z1", "power": 0.50}, "instructions": "Muy suave, progresivo"},
                {"type": "interval", "label": "Fondo suave", "duration_s": 600,
                 "target": {"zone": "Z2", "power": 0.65}, "instructions": "60-65% FTP"},
                {"type": "repeat", "label": "3 sprints activación", "repeat": 3, "steps": [
                    {"type": "interval", "label": "Sprint activación", "duration_s": 8,
                     "target": {"zone": "Z7", "power": 1.50}, "instructions": ">150% FTP, no all-out"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 120,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "repeat", "label": "2x1min umbral suave", "repeat": 2, "steps": [
                    {"type": "interval", "label": "Umbral suave", "duration_s": 60,
                     "target": {"zone": "Z4", "power": 0.95}, "instructions": "95% FTP, controlado"},
                    {"type": "interval", "label": "Recuperación", "duration_s": 120,
                     "target": {"zone": "Z1", "power": 0.47}, "instructions": "Muy suave"},
                ]},
                {"type": "interval", "label": "Vuelta a la calma", "duration_s": 600,
                 "target": {"zone": "Z1"}, "instructions": "Muy suave, terminar fresco"},
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
ALL_TEMPLATES = SWEETSPOT + THRESHOLD + VO2MAX + ANAEROBIC + SPRINT + ENDURANCE + RECOVERY + PRECOMP


def main():
    t0 = time.time()
    total = len(ALL_TEMPLATES)
    print(f"Importando {total} workouts...")

    ok = 0
    errors = 0

    for i, template in enumerate(ALL_TEMPLATES, 1):
        title = template["title"]
        print(f"[{i}/{total}] {title}")

        try:
            # Upsert por título (idempotente)
            existing = supabase.table("workout_library").select("id").eq("title", title).execute()

            if existing.data:
                workout_id = existing.data[0]["id"]
                supabase.table("workout_library").update(template).eq("id", workout_id).execute()
                embedding = rag.generate_template_embedding(template)
                if embedding:
                    supabase.table("workout_library").update({
                        "embedding": embedding, "embedding_status": "ready",
                    }).eq("id", workout_id).execute()
                    ok += 1
                else:
                    supabase.table("workout_library").update({"embedding_status": "error"}).eq("id", workout_id).execute()
                    log.error(f"Embedding failed: {title}")
                    errors += 1
            else:
                embedding = rag.generate_template_embedding(template)
                template["embedding"] = embedding
                template["embedding_status"] = "ready" if embedding else "error"
                supabase.table("workout_library").insert(template).execute()
                if embedding:
                    ok += 1
                else:
                    log.error(f"Embedding failed: {title}")
                    errors += 1

        except Exception as e:
            log.error(f"Error en {title}: {e}")
            print(f"  ERROR: {e}")
            errors += 1

    elapsed = time.time() - t0
    print(f"\nOK: {ok} | Errores: {errors} | Tiempo: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
