from tools.base import Tool, ToolResult
from db.repositories import (
    get_library_workouts,
    get_library_workout_by_id,
    schedule_library_workout,
)


class GetLibraryWorkoutsTool(Tool):
    name = "get_library_workouts"
    description = "Lista plantillas de la Workout Library con filtros opcionales (q, page, limit)."

    def run(self, args: dict) -> ToolResult:
        q = args.get("q")
        page = int(args.get("page", 1))
        limit = int(args.get("limit", 20))
        workouts = get_library_workouts(q=q, page=page, limit=limit)
        return ToolResult(success=True, data={"workouts": workouts, "page": page, "limit": limit})


class GetLibraryWorkoutDetailTool(Tool):
    name = "get_library_workout_detail"
    description = "Obtiene el detalle completo de una plantilla de la Workout Library por ID."

    def run(self, args: dict) -> ToolResult:
        workout_id = args.get("workout_id")
        if not workout_id:
            return ToolResult(success=False, error="workout_id es obligatorio.")
        workout = get_library_workout_by_id(workout_id)
        if not workout:
            return ToolResult(success=False, error=f"Plantilla '{workout_id}' no encontrada.")
        return ToolResult(success=True, data=workout)


class ScheduleLibraryWorkoutTool(Tool):
    name = "schedule_library_workout"
    description = "Crea un Planned_Workout a partir de una plantilla de la Workout Library."

    def run(self, args: dict) -> ToolResult:
        template_id = args.get("template_id")
        user_id = args.get("user_id")
        date = args.get("date")

        if not template_id or not user_id or not date:
            return ToolResult(success=False, error="template_id, user_id y date son obligatorios.")

        result = schedule_library_workout(template_id, user_id, date)
        if result is None:
            return ToolResult(success=False, error="Ya existe un entreno planificado para esa fecha.")
        if not result:
            return ToolResult(success=False, error="Plantilla no encontrada.")
        return ToolResult(success=True, data=result)
