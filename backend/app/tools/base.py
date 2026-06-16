from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class ToolResult:
    success: bool
    data: dict | None = None
    error: str | None = None


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, args: dict) -> ToolResult:
        """Ejecuta el tool con los argumentos dados."""
        ...
