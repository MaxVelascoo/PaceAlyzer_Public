from pydantic import BaseModel
from typing import Optional


# ── Workout Library schemas ───────────────────────────────────────────────────

class WorkoutTemplatePreview(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    sport_type: str
    duration_min: int
    intensity_level: str
    tags: list[str]
    structure_preview: dict   # solo primeros 3 steps
    nutrition_template: Optional[dict] = None
    est_tss: Optional[float] = None


class WorkoutTemplateDetail(WorkoutTemplatePreview):
    structure: dict           # estructura completa


class ScheduleRequest(BaseModel):
    user_id: str
    date: str                 # YYYY-MM-DD


class ScheduleResponse(BaseModel):
    planned_workout_id: str


class CreateLibraryWorkoutRequest(BaseModel):
    title: str
    description: Optional[str] = None
    sport_type: str = "cycling"
    duration_min: int
    intensity_level: str
    tags: list[str] = []
    structure: dict
    nutrition_template: Optional[dict] = None
    est_tss: Optional[float] = None


# ── Chat schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    message: str
    date: str  # YYYY-MM-DD — día del entreno en contexto


class ChatResponse(BaseModel):
    reply: str
    action_taken: Optional[str] = None   # e.g. "workout_modified", "none"
    workout_date: Optional[str] = None   # fecha del entreno modificado/creado
    workout_title: Optional[str] = None  # título del entreno
    week_plan: Optional[list] = None     # [{date, title, duration_min}, ...] para plan semanal
