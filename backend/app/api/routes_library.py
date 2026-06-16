from fastapi import APIRouter, HTTPException, Query
from models.schemas import (
    WorkoutTemplatePreview,
    WorkoutTemplateDetail,
    ScheduleRequest,
    ScheduleResponse,
    CreateLibraryWorkoutRequest,
)
from db.repositories import (
    get_library_workouts,
    get_library_workout_by_id,
    insert_library_workout,
    schedule_library_workout,
)
from services.rag_service import rag_service
from utils.logger import logger
import asyncio

router = APIRouter()


def _build_preview(row: dict) -> dict:
    """Construye el preview con solo los primeros 3 steps de la structure."""
    structure = row.get("structure") or {}
    steps = structure.get("steps", [])
    preview_structure = {**structure, "steps": steps[:3]}
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row.get("description"),
        "sport_type": row.get("sport_type", "cycling"),
        "duration_min": row.get("duration_min", 0),
        "intensity_level": row.get("intensity_level", ""),
        "tags": row.get("tags", []),
        "structure_preview": preview_structure,
        "nutrition_template": row.get("nutrition_template"),
        "est_tss": row.get("est_tss"),
    }


@router.get("/library/workouts")
async def list_library_workouts(
    q: str | None = Query(default=None, description="Filtro por título o tags"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Lista paginada de plantillas de la Workout Library."""
    workouts = get_library_workouts(q=q, page=page, limit=limit)
    return {"workouts": [_build_preview(w) for w in workouts], "page": page, "limit": limit}


@router.get("/library/workouts/{workout_id}")
async def get_library_workout(workout_id: str):
    """Detalle completo de una plantilla."""
    workout = get_library_workout_by_id(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada.")
    return workout


@router.post("/library/workouts/{workout_id}/schedule", response_model=ScheduleResponse)
async def schedule_workout(workout_id: str, req: ScheduleRequest):
    """Crea un Planned_Workout a partir de una plantilla."""
    result = schedule_library_workout(
        template_id=workout_id,
        user_id=req.user_id,
        date=req.date,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Ya existe un entreno planificado para esa fecha.")
    if not result:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada.")
    return ScheduleResponse(planned_workout_id=result["id"])


@router.post("/library/workouts")
async def create_library_workout(req: CreateLibraryWorkoutRequest):
    """
    Crea una nueva plantilla en la Workout Library y genera su embedding.
    Endpoint administrativo para gestionar la biblioteca de plantillas.
    """
    fields = req.model_dump(exclude_none=True)
    fields["embedding_status"] = "pending"

    # Insertar primero sin embedding
    created = insert_library_workout(fields)
    if not created:
        raise HTTPException(status_code=500, detail="Error al crear la plantilla.")

    # Generar embedding de forma asíncrona (no bloquea la respuesta)
    async def _generate_embedding():
        try:
            embedding = rag_service.generate_template_embedding(fields)
            if embedding:
                from db.repositories import update_library_workout
                update_library_workout(created["id"], {
                    "embedding": embedding,
                    "embedding_status": "ready",
                })
                logger.agent_end("routes_library", 0, {"embedding": "generated", "id": created["id"]})
            else:
                from db.repositories import update_library_workout
                update_library_workout(created["id"], {"embedding_status": "error"})
        except Exception as e:
            logger.error("routes_library", f"Embedding generation failed for {created['id']}: {e}")

    asyncio.create_task(_generate_embedding())

    return {"id": created["id"], "embedding_status": "pending"}
