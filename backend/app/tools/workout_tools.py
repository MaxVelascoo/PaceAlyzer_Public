from tools.base import Tool, ToolResult
from db.repositories import (
    get_planned_workout,
    update_planned_workout,
    insert_planned_workout,
    get_week_planned_workouts,
    get_blocked_days,
)


class GetCurrentPlanTool(Tool):
    name = "get_current_plan"
    description = "Lee el entreno planificado de un usuario para una fecha concreta."

    def run(self, args: dict) -> ToolResult:
        user_id = args.get("user_id")
        date = args.get("date")

        if not user_id or not date:
            return ToolResult(success=False, error="Faltan argumentos: user_id y date son obligatorios.")

        workout = get_planned_workout(user_id, date)
        if not workout:
            return ToolResult(success=False, error=f"No hay entreno planificado para el {date}.")

        return ToolResult(success=True, data=workout)


class UpdateWorkoutTool(Tool):
    name = "update_workout"
    description = "Actualiza campos de un entreno planificado por su ID."

    def run(self, args: dict) -> ToolResult:
        workout_id = args.get("workout_id")
        changes = args.get("changes")

        if not workout_id or not changes:
            return ToolResult(success=False, error="Faltan argumentos: workout_id y changes son obligatorios.")

        update_planned_workout(workout_id, changes)
        return ToolResult(success=True, data={"workout_id": workout_id, "updated_fields": list(changes.keys())})


class InsertWorkoutTool(Tool):
    name = "insert_workout"
    description = "Crea un nuevo entreno planificado para un usuario en una fecha concreta."

    def run(self, args: dict) -> ToolResult:
        user_id = args.get("user_id")
        date = args.get("date")
        fields = args.get("fields")

        if not user_id or not date or not fields:
            return ToolResult(success=False, error="Faltan argumentos: user_id, date y fields son obligatorios.")

        workout = insert_planned_workout(user_id, date, fields)
        return ToolResult(success=True, data=workout)


class GetWeekWorkoutsTool(Tool):
    name = "get_week_workouts"
    description = "Lee todos los entrenos planificados de un usuario para un rango de fechas (semana)."

    def run(self, args: dict) -> ToolResult:
        user_id = args.get("user_id")
        week_start = args.get("week_start")
        week_end = args.get("week_end")

        if not user_id or not week_start or not week_end:
            return ToolResult(success=False, error="Faltan argumentos: user_id, week_start y week_end son obligatorios.")

        workouts = get_week_planned_workouts(user_id, week_start, week_end)
        return ToolResult(success=True, data={"workouts": workouts})


class GetBlockedDaysTool(Tool):
    name = "get_blocked_days"
    description = "Lee los días bloqueados de un usuario para un rango de fechas."

    def run(self, args: dict) -> ToolResult:
        user_id = args.get("user_id")
        week_start = args.get("week_start")
        week_end = args.get("week_end")

        if not user_id or not week_start or not week_end:
            return ToolResult(success=False, error="Faltan argumentos: user_id, week_start y week_end son obligatorios.")

        rows = get_blocked_days(user_id, week_start, week_end)
        return ToolResult(success=True, data={"blocked_days": rows})
