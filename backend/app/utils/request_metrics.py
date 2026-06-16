from __future__ import annotations

import hashlib
import json
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


request_metrics_var: ContextVar["RequestMetricsCollector | None"] = ContextVar(
    "request_metrics",
    default=None,
)

CANONICAL_DURATION_KEYS = [
    "load_context",
    "operator",
    "librarian",
    "rag_service",
    "workout_editor",
    "nutrition_editor",
    "week_planner",
    "explainer",
    "tools_db",
]

PRIMARY_ROUTE_KEYS = {
    "operator",
    "librarian",
    "workout_editor",
    "nutrition_editor",
    "week_planner",
    "explainer",
}

AGENT_NAME_MAP = {
    "load_context": "load_context",
    "OperatorAgent": "operator",
    "LibraryAgent": "librarian",
    "WorkoutEditorAgent": "workout_editor",
    "NutritionEditorAgent": "nutrition_editor",
    "WeekPlannerAgent": "week_planner",
    "ExplainerAgent": "explainer",
    "RAGService": "rag_service",
}


def _canonical_agent_name(name: str) -> str | None:
    if name in AGENT_NAME_MAP:
        return AGENT_NAME_MAP[name]
    if "." in name:
        base = name.split(".", 1)[0]
        return AGENT_NAME_MAP.get(base)
    return None


def _truncate_message(message: str, max_len: int = 160) -> str:
    return message[:max_len] + "…" if len(message) > max_len else message


def _redact_user_id(user_id: str | None) -> str | None:
    if not user_id:
        return None
    digest = hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:10]
    return f"{user_id[:8]}...#{digest}"


@dataclass
class ToolCallMetric:
    name: str
    duration_ms: int
    success: bool


@dataclass
class ErrorMetric:
    component: str
    message: str
    non_blocking: bool


@dataclass
class AgentLLMMetrics:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: int = 0

    def add(self, prompt_tokens: int, completion_tokens: int, duration_ms: int) -> None:
        self.calls += 1
        self.prompt_tokens += int(prompt_tokens or 0)
        self.completion_tokens += int(completion_tokens or 0)
        self.duration_ms += int(duration_ms or 0)

    def to_dict(self) -> dict[str, int]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "duration_ms": self.duration_ms,
        }


@dataclass
class RequestMetricsCollector:
    request_id: str
    user_id: str | None
    date: str
    message: str
    request_started_monotonic: float = field(default_factory=time.monotonic)
    route: list[str] = field(default_factory=list)
    agents_called: list[str] = field(default_factory=list)
    durations_ms: dict[str, int] = field(default_factory=lambda: {key: 0 for key in CANONICAL_DURATION_KEYS})
    llm_by_agent: dict[str, AgentLLMMetrics] = field(
        default_factory=lambda: {
            "operator": AgentLLMMetrics(),
            "librarian": AgentLLMMetrics(),
            "workout_editor": AgentLLMMetrics(),
            "nutrition_editor": AgentLLMMetrics(),
            "week_planner": AgentLLMMetrics(),
            "explainer": AgentLLMMetrics(),
        }
    )
    tools_calls: list[ToolCallMetric] = field(default_factory=list)
    errors: list[ErrorMetric] = field(default_factory=list)
    rag: dict[str, Any] = field(default_factory=lambda: {
        "called": False,
        "target_duration_min": None,
        "target_tss": None,
        "sql_candidates": 0,
        "vector_results": 0,
        "reranked_results": 0,
        "top1_title": None,
        "top1_similarity": None,
        "top1_combined_score": None,
    })
    http_status: int | None = None
    action: str = "none"
    total_duration_ms: int | None = None

    def record_agent_start(self, name: str) -> None:
        canonical = _canonical_agent_name(name)
        if canonical in PRIMARY_ROUTE_KEYS and canonical not in self.route:
            self.route.append(canonical)
            self.agents_called.append(canonical)

    def record_agent_end(self, name: str, duration_ms: int) -> None:
        canonical = _canonical_agent_name(name)
        if canonical:
            self.durations_ms[canonical] = max(self.durations_ms.get(canonical, 0), int(duration_ms or 0))

    def record_llm_call(self, name: str, prompt_tokens: int, completion_tokens: int, duration_ms: int) -> None:
        canonical = _canonical_agent_name(name)
        if canonical in self.llm_by_agent:
            self.llm_by_agent[canonical].add(prompt_tokens, completion_tokens, duration_ms)

    def record_tool_call(self, name: str, duration_ms: int, success: bool) -> None:
        duration = int(duration_ms or 0)
        self.tools_calls.append(ToolCallMetric(name=name, duration_ms=duration, success=success))
        self.durations_ms["tools_db"] += duration

    def record_error(self, component: str, message: str, non_blocking: bool) -> None:
        self.errors.append(ErrorMetric(component=component, message=message[:200], non_blocking=non_blocking))

    def record_graph_end(self, duration_ms: int, action_taken: str) -> None:
        self.total_duration_ms = int(duration_ms or 0)
        self.action = action_taken or "none"

    def record_http_status(self, http_status: int) -> None:
        self.http_status = http_status

    def record_rag_summary(self, **kwargs: Any) -> None:
        self.rag["called"] = True
        for key, value in kwargs.items():
            if key in self.rag:
                self.rag[key] = value

    def build_summary(self) -> dict[str, Any]:
        if self.total_duration_ms is None:
            self.total_duration_ms = int((time.monotonic() - self.request_started_monotonic) * 1000)

        llm_total_prompt = sum(metric.prompt_tokens for metric in self.llm_by_agent.values())
        llm_total_completion = sum(metric.completion_tokens for metric in self.llm_by_agent.values())
        llm_total_duration = sum(metric.duration_ms for metric in self.llm_by_agent.values())

        principal_duration_sum = sum(
            self.durations_ms.get(key, 0)
            for key in ["load_context", "operator", "librarian", "workout_editor", "nutrition_editor", "week_planner", "explainer"]
        )
        other_overhead = max(0, self.total_duration_ms - principal_duration_sum)

        durations = {
            **self.durations_ms,
            "other_overhead": other_overhead,
        }

        return {
            "request_id": self.request_id,
            "user_id": _redact_user_id(self.user_id),
            "date": self.date,
            "message": _truncate_message(self.message),
            "http_status": self.http_status or 500,
            "action": self.action,
            "route": self.route,
            "agents_called": self.agents_called,
            "total_duration_ms": self.total_duration_ms,
            "durations_ms": durations,
            "llm": {
                "calls": sum(metric.calls for metric in self.llm_by_agent.values()),
                "prompt_tokens": llm_total_prompt,
                "completion_tokens": llm_total_completion,
                "total_tokens": llm_total_prompt + llm_total_completion,
                "duration_ms": llm_total_duration,
            },
            "llm_by_agent": {
                agent: metrics.to_dict()
                for agent, metrics in self.llm_by_agent.items()
            },
            "rag": dict(self.rag),
            "tools": {
                "calls": [
                    {
                        "name": call.name,
                        "duration_ms": call.duration_ms,
                        "success": call.success,
                    }
                    for call in self.tools_calls
                ],
                "total_calls": len(self.tools_calls),
                "success_calls": sum(1 for call in self.tools_calls if call.success),
                "error_calls": sum(1 for call in self.tools_calls if not call.success),
                "total_duration_ms": sum(call.duration_ms for call in self.tools_calls),
            },
            "errors": [
                {
                    "component": err.component,
                    "message": err.message,
                    "non_blocking": err.non_blocking,
                }
                for err in self.errors
            ],
        }

    def build_log_line(self) -> str:
        summary = self.build_summary()
        return (
            f"REQUEST SUMMARY request_id={summary['request_id']} "
            f"status={summary['http_status']} action={summary['action']} "
            f"route={summary['route']} total_ms={summary['total_duration_ms']} "
            f"llm_calls={summary['llm']['calls']} total_tokens={summary['llm']['total_tokens']} "
            f"tools={summary['tools']['total_calls']} rag_called={summary['rag']['called']}"
        )


def start_request_metrics(request_id: str, user_id: str | None, date: str, message: str) -> RequestMetricsCollector:
    collector = RequestMetricsCollector(
        request_id=request_id,
        user_id=user_id,
        date=date,
        message=message,
    )
    request_metrics_var.set(collector)
    return collector


def get_request_metrics_collector() -> RequestMetricsCollector | None:
    return request_metrics_var.get()


def clear_request_metrics() -> None:
    request_metrics_var.set(None)


def summary_to_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
