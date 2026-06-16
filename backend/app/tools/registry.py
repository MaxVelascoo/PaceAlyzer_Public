from tools.base import Tool, ToolResult
from tools.workout_tools import GetCurrentPlanTool, UpdateWorkoutTool, InsertWorkoutTool, GetWeekWorkoutsTool, GetBlockedDaysTool
from tools.nutrition_tools import GetNutritionTool, UpdateNutritionTool
from tools.library_tools import GetLibraryWorkoutsTool, GetLibraryWorkoutDetailTool, ScheduleLibraryWorkoutTool
import time


class ToolRegistry:
    """
    Registro central de tools disponibles.
    Los agentes y el orquestador invocan tools a través de aquí.
    Los LLMs nunca escriben en la DB directamente — solo a través de tools.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self):
        for tool in [
            GetCurrentPlanTool(),
            UpdateWorkoutTool(),
            InsertWorkoutTool(),
            GetWeekWorkoutsTool(),
            GetBlockedDaysTool(),
            GetNutritionTool(),
            UpdateNutritionTool(),
            GetLibraryWorkoutsTool(),
            GetLibraryWorkoutDetailTool(),
            ScheduleLibraryWorkoutTool(),
        ]:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def execute(self, name: str, args: dict) -> ToolResult:
        tool = self.get(name)
        if not tool:
            from utils.logger import logger
            logger.tool_call(name, args, False, "tool not found in registry", duration_ms=0)
            return ToolResult(success=False, error=f"Tool '{name}' no encontrado en el registry.")

        from utils.logger import logger
        t0 = time.monotonic()
        result = tool.run(args)
        duration_ms = int((time.monotonic() - t0) * 1000)
        detail = result.error if not result.success else (
            str(list(result.data.keys())) if result.data else None
        )
        # get_current_plan sin resultado no es un error, es un estado válido
        warn_on_miss = name != "get_current_plan"
        logger.tool_call(name, args, result.success, detail, warn_on_miss=warn_on_miss, duration_ms=duration_ms)
        return result

    def list_tools(self) -> list[dict]:
        """Devuelve la lista de tools disponibles (útil para el LLM orchestrator)."""
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]


# Instancia global — se importa desde los agentes
registry = ToolRegistry()
