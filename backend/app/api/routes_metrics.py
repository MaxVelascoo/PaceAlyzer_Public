from fastapi import APIRouter, HTTPException
from services.metrics_service import recalculate_metrics, recalculate_mmp_history
from db.repositories import delete_planned_workout

router = APIRouter()


@router.post("/metrics/recalculate")
async def recalculate(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id es obligatorio.")
    result = recalculate_metrics(user_id)
    return result


@router.post("/metrics/recalculate-mmp")
async def recalculate_mmp(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id es obligatorio.")
    result = recalculate_mmp_history(user_id)
    return result


@router.delete("/planned-workouts/{workout_id}")
async def delete_workout(workout_id: str, user_id: str):
    if not user_id or not workout_id:
        raise HTTPException(status_code=400, detail="user_id y workout_id son obligatorios.")

    delete_planned_workout(workout_id, user_id)
    return {"deleted": workout_id}
