from tools.base import Tool, ToolResult
from db.repositories import get_planned_workout, update_planned_workout


class GetNutritionTool(Tool):
    name = "get_nutrition"
    description = "Lee la nutrición del entreno planificado de un usuario para una fecha concreta."

    def run(self, args: dict) -> ToolResult:
        user_id = args.get("user_id")
        date = args.get("date")

        if not user_id or not date:
            return ToolResult(success=False, error="Faltan argumentos: user_id y date son obligatorios.")

        workout = get_planned_workout(user_id, date)
        if not workout:
            return ToolResult(success=False, error=f"No hay entreno planificado para el {date}.")

        nutrition = workout.get("nutrition")
        if not nutrition:
            return ToolResult(success=False, error=f"No hay nutrición definida para el {date}.")

        return ToolResult(success=True, data={"nutrition": nutrition, "workout_id": workout["id"]})


class UpdateNutritionTool(Tool):
    name = "update_nutrition"
    description = "Actualiza la nutrición de un entreno planificado por su ID."

    def run(self, args: dict) -> ToolResult:
        workout_id = args.get("workout_id")
        nutrition = args.get("nutrition")

        if not workout_id or nutrition is None:
            return ToolResult(success=False, error="Faltan argumentos: workout_id y nutrition son obligatorios.")

        update_planned_workout(workout_id, {"nutrition": nutrition})
        return ToolResult(success=True, data={"workout_id": workout_id})
