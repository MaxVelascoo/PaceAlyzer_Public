"""
Sistema de logging estructurado para PaceAlyzer.

Uso:
    from utils.logger import logger, trace_id_var
    trace_id_var.set("abc123")   # una vez en el orchestrator
    logger.agent_start("WorkoutEditorAgent", {"date": "2026-03-31"})
"""

import logging
import time
import os
from contextvars import ContextVar
from typing import Any

from utils.request_metrics import get_request_metrics_collector, summary_to_json

# ─── Trace ID por petición ────────────────────────────────────────────────────
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="--------")

# ─── Configuración del logger base ───────────────────────────────────────────
_ENV = os.getenv("ENV", "development")

_base_logger = logging.getLogger("pazey")
_base_logger.setLevel(logging.DEBUG)

if not _base_logger.handlers:
    _handler = logging.StreamHandler()
    if _ENV == "production":
        # JSON compacto para sistemas de logs externos
        _handler.setFormatter(logging.Formatter('%(message)s'))
    else:
        # Legible para desarrollo
        _handler.setFormatter(logging.Formatter('%(message)s'))
    _base_logger.addHandler(_handler)


# ─── Colores para desarrollo ──────────────────────────────────────────────────
_RESET  = "\033[0m"
_GREY   = "\033[90m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_BOLD   = "\033[1m"

_LEVEL_COLORS = {
    "INFO":    _CYAN,
    "SUCCESS": _GREEN,
    "WARNING": _YELLOW,
    "ERROR":   _RED,
    "DEBUG":   _GREY,
}


class PazeyLogger:
    """Logger estructurado con trace_id automático."""

    def _log(self, level: str, agent: str, event: str, data: dict | None = None):
        trace = trace_id_var.get()
        ts = time.strftime("%H:%M:%S")
        color = _LEVEL_COLORS.get(level, _RESET)

        # Formatear data como string compacto
        data_str = ""
        if data:
            parts = [f"{k}={_truncate(v)}" for k, v in data.items()]
            data_str = "  " + _GREY + " | ".join(parts) + _RESET

        line = (
            f"{_GREY}{ts}{_RESET} "
            f"{color}{level:<7}{_RESET} "
            f"{_GREY}[{trace}]{_RESET} "
            f"{_BOLD}{agent:<24}{_RESET} "
            f"{event}"
            f"{data_str}"
        )
        _base_logger.info(line)

    # ── Eventos de agente ─────────────────────────────────────────────────────

    def agent_start(self, agent: str, context: dict | None = None):
        collector = get_request_metrics_collector()
        if collector:
            try:
                collector.record_agent_start(agent)
            except Exception:
                pass
        self._log("INFO", agent, "▶ START", context)
        
    def agent_input(self, agent: str, prompt: str):
        """Loguea el prompt completo enviado al LLM sin truncar."""
        trace = trace_id_var.get()
        ts = time.strftime("%H:%M:%S")
        print(f"{_GREY}{ts}{_RESET} {_YELLOW}DEBUG  {_RESET} {_GREY}[{trace}]{_RESET} {_BOLD}{agent:<24}{_RESET} → INPUT\n{prompt}\n")

    def agent_output(self, agent: str, output: str | dict):
        """Loguea el output recibido del LLM sin truncar."""
        trace = trace_id_var.get()
        ts = time.strftime("%H:%M:%S")
        text = str(output) if isinstance(output, dict) else output
        print(f"{_GREY}{ts}{_RESET} {_YELLOW}DEBUG  {_RESET} {_GREY}[{trace}]{_RESET} {_BOLD}{agent:<24}{_RESET} ← OUTPUT\n{text}\n")

    def agent_end(self, agent: str, duration_ms: int, result: dict | None = None):
        collector = get_request_metrics_collector()
        if collector:
            try:
                collector.record_agent_end(agent, duration_ms)
            except Exception:
                pass
        data = {"duration": f"{duration_ms}ms", **(result or {})}
        self._log("SUCCESS", agent, "■ END  ", data)

    def agent_skip(self, agent: str, reason: str):
        self._log("DEBUG", agent, "○ SKIP ", {"reason": reason})

    # ── Eventos de tool ───────────────────────────────────────────────────────

    def tool_call(
        self,
        tool: str,
        args: dict,
        success: bool,
        detail: str | None = None,
        warn_on_miss: bool = True,
        duration_ms: int | None = None,
    ):
        collector = get_request_metrics_collector()
        if collector:
            try:
                collector.record_tool_call(tool, int(duration_ms or 0), success)
            except Exception:
                pass
        status = "✓" if success else "✗"
        level = "SUCCESS" if success else ("WARNING" if not warn_on_miss else "ERROR")
        data = {k: _truncate(v) for k, v in args.items() if k != "changes"}
        if duration_ms is not None:
            data["duration"] = f"{duration_ms}ms"
        if detail:
            data["detail"] = detail
        self._log(level, f"TOOL:{tool}", f"{status} CALL ", data)

    # ── Eventos de LLM ───────────────────────────────────────────────────────

    def llm_call(self, agent: str, prompt_tokens: int, completion_tokens: int, duration_ms: int):
        collector = get_request_metrics_collector()
        if collector:
            try:
                collector.record_llm_call(agent, prompt_tokens, completion_tokens, duration_ms)
            except Exception:
                pass
        self._log("INFO", agent, "◈ LLM  ", {
            "prompt_tk": prompt_tokens,
            "completion_tk": completion_tokens,
            "total_tk": prompt_tokens + completion_tokens,
            "duration": f"{duration_ms}ms",
        })

    # ── Eventos de grafo ──────────────────────────────────────────────────────

    def graph_start(self, user_id: str, message: str, date: str):
        self._log("INFO", "GRAPH", "━━ REQUEST START ━━", {
            "user": user_id[:8] + "...",
            "date": date,
            "msg": message[:60],
        })

    def graph_end(self, duration_ms: int, action_taken: str):
        collector = get_request_metrics_collector()
        if collector:
            try:
                collector.record_graph_end(duration_ms, action_taken)
            except Exception:
                pass
        self._log("SUCCESS", "GRAPH", "━━ REQUEST END   ━━", {
            "duration": f"{duration_ms}ms",
            "action": action_taken,
        })

    def rag_summary(self, **kwargs: Any):
        collector = get_request_metrics_collector()
        if collector:
            try:
                collector.record_rag_summary(**kwargs)
            except Exception:
                pass

    def request_summary(self, summary: dict[str, Any]):
        try:
            trace = trace_id_var.get()
            self._log("INFO", "GRAPH", "━━ REQUEST SUMMARY ━", {
                "status": summary.get("http_status"),
                "action": summary.get("action"),
                "route": summary.get("route"),
                "duration": f"{summary.get('total_duration_ms', 0)}ms",
                "tokens": summary.get("llm", {}).get("total_tokens", 0),
                "llm_calls": summary.get("llm", {}).get("calls", 0),
            })
            _base_logger.info(f"REQUEST_METRICS_JSON {summary_to_json(summary)}")
        except Exception:
            # Nunca romper la request por fallo de métricas
            _base_logger.exception("Failed to log request summary")

    # ── Errores ───────────────────────────────────────────────────────────────

    def error(self, agent: str, error: str, context: dict | None = None, non_blocking: bool = False):
        collector = get_request_metrics_collector()
        if collector:
            try:
                collector.record_error(agent, error, non_blocking)
            except Exception:
                pass
        data = {"error": error[:120], **(context or {})}
        self._log("ERROR", agent, "✗ ERROR", data)

    def warning(self, agent: str, msg: str, context: dict | None = None):
        data = {"msg": msg, **(context or {})}
        self._log("WARNING", agent, "⚠ WARN ", data)


def _truncate(v: Any, max_len: int = 60) -> str:
    """Convierte un valor a string truncado para los logs."""
    if isinstance(v, dict):
        keys = list(v.keys())
        return f"{{keys:{keys[:4]}}}"
    if isinstance(v, list):
        # Si es lista de strings cortos, mostrarlos directamente
        if all(isinstance(i, str) and len(i) < 30 for i in v):
            return str(v)
        return f"[{len(v)} items]"
    s = str(v)
    return s[:max_len] + "…" if len(s) > max_len else s


# Instancia global
logger = PazeyLogger()
