"""
regenerate_embeddings.py — Genera embeddings desde la columna embedding_text.

Lee cada plantilla con embedding_status = 'pending' (o todas si se pasa --force),
toma el texto de la columna embedding_text, lo convierte a vector con
text-embedding-3-large (3072 dims) y actualiza embedding + embedding_status.

Uso:
    cd PaceAlyzer_Backend
    python scripts/regenerate_embeddings.py              # Solo las pendientes
    python scripts/regenerate_embeddings.py --force      # Todas (regenerar)
    python scripts/regenerate_embeddings.py --dry-run    # Ver qué haría sin ejecutar
"""

import sys
import os
import time
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
APP_DIR = os.path.join(BACKEND_DIR, "app")
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from openai import OpenAI
from db.supabase_client import supabase

# ── Config ────────────────────────────────────────────────────────────────────

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
DELAY_BETWEEN_REQUESTS = 0.3  # segundos entre llamadas para respetar rate limit
BATCH_SIZE = 10  # filas por commit parcial para poder relanzar si falla

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_embedding(text: str, max_retries: int = 3) -> list[float] | None:
    """Genera embedding con retry exponencial."""
    for attempt in range(max_retries):
        try:
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            return response.data[0].embedding
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"    ⚠ Error (intento {attempt + 1}): {e}. Esperando {wait}s...")
                time.sleep(wait)
            else:
                print(f"    ✗ Fallo tras {max_retries} intentos: {e}")
                return None


def load_templates(force: bool) -> list[dict]:
    """Carga las plantillas a procesar."""
    query = (
        supabase.table("workout_library")
        .select("id, title, embedding_text, embedding_status")
        .eq("sport_type", "cycling")
    )
    if not force:
        query = query.eq("embedding_status", "pending")

    res = query.order("title").execute()
    return res.data or []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Regenera embeddings desde embedding_text")
    parser.add_argument("--force", action="store_true",
                        help="Procesar todas las plantillas, no solo las pending")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostrar qué haría sin ejecutar ninguna llamada a OpenAI")
    args = parser.parse_args()

    templates = load_templates(force=args.force)

    if not templates:
        print("✓ No hay plantillas para procesar.")
        return

    # Filtrar las que no tienen embedding_text
    no_text = [t for t in templates if not t.get("embedding_text")]
    to_process = [t for t in templates if t.get("embedding_text")]

    print(f"\n{'='*65}")
    print(f"  Modelo:    {EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS} dims)")
    print(f"  Total:     {len(templates)} plantillas seleccionadas")
    print(f"  A procesar: {len(to_process)} con embedding_text")
    if no_text:
        print(f"  Sin texto:  {len(no_text)} (se saltarán)")
    if args.dry_run:
        print(f"  Modo:       DRY RUN — no se escribe nada")
    print(f"{'='*65}\n")

    if no_text:
        print("  Plantillas SIN embedding_text (se saltan):")
        for t in no_text:
            print(f"    - {t['title']} ({t['id'][:8]}...)")
        print()

    if args.dry_run:
        print("  Plantillas que se procesarían:")
        for t in to_process:
            text_preview = (t["embedding_text"] or "")[:80].replace("\n", " ")
            print(f"  ✓ {t['title']}")
            print(f"    → {text_preview}...")
        print(f"\n  Total: {len(to_process)} embeddings a generar")
        cost_estimate = len(to_process) * 3072 * 0.13 / 1_000_000
        print(f"  Coste estimado: ~${cost_estimate:.4f} USD")
        return

    # ── Procesado real ────────────────────────────────────────────────────────
    ok = 0
    errors = []
    t_start = time.monotonic()

    for i, template in enumerate(to_process, 1):
        title = template["title"]
        template_id = template["id"]
        embed_text = template["embedding_text"]

        print(f"[{i}/{len(to_process)}] {title[:55]}", end="", flush=True)

        # Generar embedding directamente sin marcar como processing
        vector = generate_embedding(embed_text)

        if vector is None:
            print(f" ✗ ERROR")
            supabase.table("workout_library").update({
                "embedding_status": "error"
            }).eq("id", template_id).execute()
            errors.append(title)
            continue

        # Verificar dimensión
        if len(vector) != EMBEDDING_DIMENSIONS:
            print(f" ✗ Dimensión incorrecta: {len(vector)} (esperado {EMBEDDING_DIMENSIONS})")
            supabase.table("workout_library").update({
                "embedding_status": "error"
            }).eq("id", template_id).execute()
            errors.append(title)
            continue

        # Guardar embedding
        supabase.table("workout_library").update({
            "embedding": vector,
            "embedding_status": "ready",
        }).eq("id", template_id).execute()

        ok += 1
        print(f" ✓ ({len(vector)} dims)")

        # Delay entre requests
        if i < len(to_process):
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # ── Resumen ───────────────────────────────────────────────────────────────
    elapsed = time.monotonic() - t_start
    print(f"\n{'='*65}")
    print(f"  Completado en {elapsed:.1f}s")
    print(f"  ✓ {ok}/{len(to_process)} embeddings generados")
    if errors:
        print(f"  ✗ {len(errors)} errores:")
        for e in errors:
            print(f"    - {e}")
    print(f"{'='*65}\n")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
