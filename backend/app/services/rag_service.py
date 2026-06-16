import time
from typing import Any

from db.supabase_client import supabase
from llm.client import client
from services.workout_analyzer import build_enriched_embedding_text
from utils.logger import logger

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
MIN_SIMILARITY = 0.45
TOP_K_VECTOR = 20
TOP_K_FINAL = 3

COMPATIBLE_VALUES = {
    "primary_goal": {
        ("sweetspot", "threshold"),
        ("threshold", "sweetspot"),
        ("tempo", "sweetspot"),
        ("sweetspot", "tempo"),
        ("strength_torque", "neuromuscular_sprint"),
        ("neuromuscular_sprint", "strength_torque"),
        ("anaerobic_frc", "vo2max"),
        ("vo2max", "anaerobic_frc"),
    },
    "work_zone": {
        ("Z3_Z4", "Z4"),
        ("Z4", "Z3_Z4"),
        ("Z4_Z5", "Z4"),
        ("Z4", "Z4_Z5"),
        ("Z4_Z5", "Z5"),
        ("Z5", "Z4_Z5"),
        ("Z6_Z7", "Z5"),
        ("mixed", "Z4"),
        ("mixed", "Z5"),
        ("mixed", "Z3_Z4"),
    },
    "structure_type": {
        ("mixed", "long_intervals"),
        ("long_intervals", "mixed"),
        ("short_intervals", "microbursts"),
        ("microbursts", "short_intervals"),
        ("sprints", "torque_sprints"),
        ("torque_sprints", "sprints"),
    },
    "fatigue_suitability": {
        ("fresh_only", "normal_or_fresh"),
        ("normal_or_fresh", "fresh_only"),
        ("fatigued_ok", "very_fatigued_ok"),
        ("very_fatigued_ok", "fatigued_ok"),
    },
    "duration_class": {
        ("very_short", "short"),
        ("short", "very_short"),
        ("short", "medium"),
        ("medium", "short"),
        ("medium", "long"),
        ("long", "medium"),
    },
}

METADATA_MATCH_WEIGHTS = {
    "primary_goal": 0.40,
    "work_zone": 0.25,
    "structure_type": 0.20,
    "fatigue_suitability": 0.10,
    "duration_class": 0.05,
}


def _as_clean_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value).strip() or None


class RAGService:
    def build_embedding_text(self, template: dict) -> str:
        return build_enriched_embedding_text(template)

    def build_query_text(self, athlete_context: dict, session_type: str = "") -> str:
        if session_type and "SEMANTIC_LABELS:" in session_type:
            return session_type

        parts = []
        if session_type:
            parts.append(f"SUMMARY: {session_type}")

        tsb = athlete_context.get("tsb")
        fatigue_label = None
        if tsb is not None:
            if tsb < -20:
                fatigue_label = "very_fatigued_ok"
            elif tsb < -10:
                fatigue_label = "fatigued_ok"
            elif tsb > 10:
                fatigue_label = "normal_or_fresh"

        if fatigue_label:
            parts.append(f"SEMANTIC_LABELS:\nfatigue_suitability={fatigue_label}")

        return "\n\n".join(parts) if parts else "SUMMARY: entreno ciclismo"

    def parse_semantic_labels(self, generated_query: str) -> dict[str, Any]:
        labels: dict[str, Any] = {}
        if not generated_query:
            return labels

        in_labels = False
        for raw_line in generated_query.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.upper().startswith("SEMANTIC_LABELS"):
                in_labels = True
                continue
            if not in_labels or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if key == "secondary_goals":
                labels[key] = [item.strip() for item in value.split(",") if item.strip()]
            elif value:
                labels[key] = value

        return labels

    def are_compatible(self, field: str, actual: str | None, expected: str | None) -> bool:
        if not actual or not expected:
            return False
        if actual == expected:
            return True
        return (actual, expected) in COMPATIBLE_VALUES.get(field, set()) or (
            expected,
            actual,
        ) in COMPATIBLE_VALUES.get(field, set())

    def metadata_match_score(self, template: dict, query_labels: dict[str, Any]) -> float:
        matched = 0.0
        total_weight = 0.0

        for field, weight in METADATA_MATCH_WEIGHTS.items():
            expected = _as_clean_str(query_labels.get(field))
            actual = _as_clean_str(template.get(field))
            if expected is None:
                continue

            total_weight += weight
            if actual == expected:
                matched += weight
            elif self.are_compatible(field, actual, expected):
                matched += weight * 0.5

        if total_weight == 0:
            return 0.5
        return matched / total_weight

    def _infer_tsb_category(self, athlete_context: dict) -> str | None:
        tsb_category = _as_clean_str(athlete_context.get("tsb_category"))
        if tsb_category:
            return tsb_category

        tsb = athlete_context.get("tsb")
        if tsb is None:
            return None
        if tsb <= -20:
            return "very_fatigued"
        if tsb <= -8:
            return "fatigued"
        if tsb < 8:
            return "normal"
        return "fresh"

    def context_fit_score(self, template: dict, athlete_context: dict) -> float:
        tsb_category = self._infer_tsb_category(athlete_context)
        suitability = _as_clean_str(template.get("fatigue_suitability"))

        if tsb_category is None or suitability is None:
            return 0.7

        scores = {
            "very_fatigued": {
                "very_fatigued_ok": 1.0,
                "fatigued_ok": 0.7,
                "normal_or_fresh": 0.2,
                "fresh_only": 0.0,
            },
            "fatigued": {
                "very_fatigued_ok": 1.0,
                "fatigued_ok": 1.0,
                "normal_or_fresh": 0.6,
                "fresh_only": 0.2,
            },
            "normal": {
                "very_fatigued_ok": 0.8,
                "fatigued_ok": 0.9,
                "normal_or_fresh": 1.0,
                "fresh_only": 0.8,
            },
            "fresh": {
                "very_fatigued_ok": 1.0,
                "fatigued_ok": 1.0,
                "normal_or_fresh": 1.0,
                "fresh_only": 1.0,
            },
        }
        return scores.get(tsb_category, {}).get(suitability, 0.7)

    def duration_fit_score(self, template: dict, athlete_context: dict) -> float:
        target = athlete_context.get("target_duration_min")
        duration = template.get("duration_min")
        if target is None or duration is None:
            return 0.5

        diff = abs(float(duration) - float(target))
        return max(0.0, 1.0 - diff / max(float(target), 60.0))

    def tss_fit_score(self, template: dict, athlete_context: dict) -> float | None:
        target_tss = athlete_context.get("target_tss")
        if target_tss is None:
            return None

        est_tss = template.get("est_tss")
        if est_tss is None:
            return 0.5

        return max(0.0, 1.0 - abs(float(est_tss) - float(target_tss)) / 200.0)

    def hard_penalty(self, template: dict, query_labels: dict[str, Any], athlete_context: dict) -> float:
        penalty = 0.0

        q_goal = _as_clean_str(query_labels.get("primary_goal"))
        t_goal = _as_clean_str(template.get("primary_goal"))
        tsb_category = self._infer_tsb_category(athlete_context)
        suitability = _as_clean_str(template.get("fatigue_suitability"))

        if q_goal == "recovery" and t_goal != "recovery":
            penalty += 0.50

        if q_goal in ["threshold", "vo2max", "anaerobic_frc"] and t_goal in ["recovery", "endurance"]:
            penalty += 0.35

        if q_goal == "endurance" and t_goal in ["vo2max", "anaerobic_frc", "neuromuscular_sprint"]:
            penalty += 0.30

        if tsb_category == "very_fatigued" and suitability == "fresh_only":
            penalty += 0.50

        if tsb_category == "fatigued" and suitability == "fresh_only":
            penalty += 0.20

        return penalty

    def rerank_templates(
        self,
        templates: list[dict],
        generated_semantic_labels: dict[str, Any],
        athlete_context: dict,
        top_k: int = 3,
        min_similarity: float | None = None,
    ) -> list[dict]:
        if not templates:
            return []

        threshold = MIN_SIMILARITY if min_similarity is None else min_similarity
        filtered = []
        for template in templates:
            similarity = float(template.get("similarity") or template.get("cosine_similarity") or 0.0)
            if similarity < threshold:
                continue

            metadata_score = self.metadata_match_score(template, generated_semantic_labels)
            context_score = self.context_fit_score(template, athlete_context)
            duration_score = self.duration_fit_score(template, athlete_context)
            tss_score = self.tss_fit_score(template, athlete_context)
            penalty = self.hard_penalty(template, generated_semantic_labels, athlete_context)

            if tss_score is None:
                combined_score = (
                    0.65 * similarity
                    + 0.20 * metadata_score
                    + 0.10 * context_score
                    + 0.05 * duration_score
                    - penalty
                )
            else:
                combined_score = (
                    0.60 * similarity
                    + 0.20 * metadata_score
                    + 0.10 * context_score
                    + 0.05 * duration_score
                    + 0.05 * tss_score
                    - penalty
                )

            reranked = {
                **template,
                "similarity": similarity,
                "cosine_similarity": similarity,
                "metadata_match_score": metadata_score,
                "context_fit_score": context_score,
                "duration_fit_score": duration_score,
                "tss_fit_score": tss_score,
                "hard_penalty": penalty,
                "combined_score": combined_score,
            }
            filtered.append(reranked)

        ranked = sorted(
            filtered,
            key=lambda item: (item["combined_score"], item["cosine_similarity"]),
            reverse=True,
        )[:top_k]

        for rank, template in enumerate(ranked, start=1):
            template["rank"] = rank

        return ranked

    def generate_embedding(self, text: str, max_retries: int = 3) -> list[float] | None:
        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("rag_service", f"Embedding failed after {max_retries} retries: {e}")
                    return None

    def generate_template_embedding(self, template: dict, max_retries: int = 3) -> list[float] | None:
        text = self.build_embedding_text(template)
        return self.generate_embedding(text, max_retries)

    def _sql_filter(
        self,
        target_duration_min: int,
        tsb: float | None,
        tolerance: float,
    ) -> list[dict]:
        min_dur = int(target_duration_min * (1 - tolerance))
        max_dur = int(target_duration_min * (1 + tolerance))

        logger.agent_start("RAGService.sql_filter", {
            "target_duration": target_duration_min,
            "range": f"{min_dur}-{max_dur}min",
            "tsb": tsb,
            "tolerance": f"{int(tolerance * 100)}%",
        })

        query = (
            supabase.table("workout_library")
            .select(
                "id, title, description, sport_type, duration_min, intensity_level, "
                "tags, structure, nutrition_template, est_tss, embedding, "
                "primary_goal, secondary_goals, work_zone, structure_type, "
                "fatigue_suitability, load_level, duration_class, embedding_text"
            )
            .eq("sport_type", "cycling")
            .eq("embedding_status", "ready")
            .gte("duration_min", min_dur)
            .lte("duration_min", max_dur)
        )

        intensity_filter_applied = False
        if tsb is not None and tsb < -20:
            query = query.not_.in_("intensity_level", ["hard", "very_hard"])
            intensity_filter_applied = True

        res = query.execute()
        candidates = res.data or []

        logger.agent_end("RAGService.sql_filter", 0, {
            "candidates_found": len(candidates),
            "intensity_filter": intensity_filter_applied,
            "sample_titles": [c.get("title", "")[:30] for c in candidates[:3]],
        })
        return candidates

    def _vector_search(
        self,
        candidates: list[dict],
        query_vector: list[float],
    ) -> list[dict]:
        if not candidates:
            return []

        candidate_ids = [c["id"] for c in candidates]
        res = supabase.rpc(
            "match_library_workouts",
            {
                "query_embedding": query_vector,
                "candidate_ids": candidate_ids,
                "match_count": TOP_K_VECTOR,
                "min_similarity": MIN_SIMILARITY,
            },
        ).execute()

        return res.data or []

    def search(
        self,
        athlete_context: dict,
        target_duration_min: int,
        target_tss: float,
        session_type: str = "",
    ) -> list[dict]:
        t0 = time.monotonic()
        tsb = athlete_context.get("tsb")

        total_res = supabase.table("workout_library").select("id", count="exact").eq("sport_type", "cycling").execute()
        ready_res = supabase.table("workout_library").select("id", count="exact").eq("sport_type", "cycling").eq("embedding_status", "ready").execute()
        logger.agent_start("RAGService", {
            "total_workouts": total_res.count,
            "ready_embeddings": ready_res.count,
            "target_duration": target_duration_min,
            "target_tss": target_tss,
            "tsb": tsb,
        })
        logger.rag_summary(
            target_duration_min=target_duration_min,
            target_tss=target_tss,
            sql_candidates=0,
            vector_results=0,
            reranked_results=0,
            top1_title=None,
            top1_similarity=None,
            top1_combined_score=None,
        )

        candidates = self._sql_filter(target_duration_min, tsb, tolerance=0.4)
        if len(candidates) < 5:
            logger.agent_start("RAGService", {"msg": "Relaxing duration filter to ±60%"})
            candidates = self._sql_filter(target_duration_min, tsb, tolerance=0.6)

        if not candidates:
            logger.rag_summary(sql_candidates=0, vector_results=0, reranked_results=0)
            logger.error("rag_service", "No candidates found after relaxed filter")
            return []

        query_text = self.build_query_text(athlete_context, session_type)
        generated_labels = self.parse_semantic_labels(session_type)

        logger.agent_start("RAGService.query_text", {"full_query": query_text})

        query_vector = self.generate_embedding(query_text)
        if query_vector is None:
            logger.rag_summary(sql_candidates=len(candidates), vector_results=0, reranked_results=0)
            logger.error("rag_service", "Failed to generate query embedding")
            return []

        top_results = self._vector_search(candidates, query_vector)
        if not top_results:
            logger.rag_summary(sql_candidates=len(candidates), vector_results=0, reranked_results=0)
            logger.error("rag_service", f"No results with similarity >= {MIN_SIMILARITY}")
            return []

        all_results_log = []
        for result in top_results[:10]:
            title = result.get("title", "")[:40]
            sim = result.get("similarity", 0)
            tss = result.get("est_tss", 0)
            all_results_log.append(f"{title} (sim={sim:.3f}, tss={tss})")
        logger.agent_start("RAGService.vector_results", {
            "count": len(top_results),
            "top10": " | ".join(all_results_log),
        })

        candidates_by_id = {candidate["id"]: candidate for candidate in candidates}
        enriched_results = []
        for result in top_results:
            enriched_results.append({**candidates_by_id.get(result["id"], {}), **result})

        reranked = self.rerank_templates(
            templates=enriched_results,
            generated_semantic_labels=generated_labels,
            athlete_context=athlete_context,
            top_k=TOP_K_FINAL,
            min_similarity=MIN_SIMILARITY,
        )
        if not reranked:
            logger.rag_summary(sql_candidates=len(candidates), vector_results=len(top_results), reranked_results=0)
            logger.error("rag_service", f"No results with similarity >= {MIN_SIMILARITY} after reranking")
            return []

        duration_ms = int((time.monotonic() - t0) * 1000)
        top_details = {}
        for i, template in enumerate(reranked, start=1):
            title = template.get("title", "")[:30]
            top_details[f"top{i}"] = (
                f"{title} (sim={template.get('cosine_similarity', 0):.3f}, "
                f"meta={template.get('metadata_match_score', 0):.3f}, "
                f"ctx={template.get('context_fit_score', 0):.3f}, "
                f"score={template.get('combined_score', 0):.3f})"
            )

        logger.agent_end("RAGService", duration_ms, {
            "candidates": len(candidates),
            "vector_results": len(top_results),
            "reranked_results": len(reranked),
            "top3_ids": [t["id"] for t in reranked],
            "target_tss": target_tss,
            "duration_ms": duration_ms,
            **top_details,
        })
        top1 = reranked[0] if reranked else {}
        logger.rag_summary(
            sql_candidates=len(candidates),
            vector_results=len(top_results),
            reranked_results=len(reranked),
            top1_title=top1.get("title"),
            top1_similarity=top1.get("cosine_similarity"),
            top1_combined_score=top1.get("combined_score"),
        )

        return reranked


rag_service = RAGService()
