import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.request_metrics import RequestMetricsCollector


class RequestMetricsCollectorTests(unittest.TestCase):
    def test_build_summary_aggregates_llm_tools_and_overhead(self):
        collector = RequestMetricsCollector(
            request_id="abc12345",
            user_id="user-123456789",
            date="2026-06-06",
            message="ponme un entreno de umbral para mañana",
        )

        collector.record_agent_start("OperatorAgent")
        collector.record_agent_end("OperatorAgent", 1200)
        collector.record_agent_start("LibraryAgent")
        collector.record_agent_end("LibraryAgent", 3200)
        collector.record_agent_start("ExplainerAgent")
        collector.record_agent_end("ExplainerAgent", 400)

        collector.record_llm_call("OperatorAgent", 100, 20, 1200)
        collector.record_llm_call("LibraryAgent", 200, 30, 1500)
        collector.record_tool_call("get_current_plan", 80, True)
        collector.record_rag_summary(
            target_duration_min=90,
            target_tss=70.0,
            sql_candidates=10,
            vector_results=5,
            reranked_results=3,
            top1_title="TH-01",
            top1_similarity=0.82,
            top1_combined_score=0.84,
        )
        collector.record_graph_end(6000, "workout_modified")
        collector.record_http_status(200)

        summary = collector.build_summary()

        self.assertEqual(summary["request_id"], "abc12345")
        self.assertEqual(summary["http_status"], 200)
        self.assertEqual(summary["action"], "workout_modified")
        self.assertEqual(summary["route"], ["operator", "librarian", "explainer"])
        self.assertEqual(summary["llm"]["calls"], 2)
        self.assertEqual(summary["llm"]["total_tokens"], 350)
        self.assertEqual(summary["tools"]["total_calls"], 1)
        self.assertEqual(summary["durations_ms"]["tools_db"], 80)
        self.assertEqual(summary["rag"]["top1_title"], "TH-01")
        self.assertEqual(summary["durations_ms"]["other_overhead"], 1200)


if __name__ == "__main__":
    unittest.main()
