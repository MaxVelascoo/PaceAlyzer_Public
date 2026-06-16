#!/usr/bin/env python3
"""
Generate TFG figures from existing evaluation outputs.

This script DOES NOT call the backend, agents, OpenAI, Supabase, or any runtime system.
It only reads already generated JSON/CSV files and creates the final PNG figures used
in the report.

Figures generated:
- figures/phase_metrics_bar.png
- figures/rerank_position_relevance_heatmap.png
- figures/operator_overall_metrics_bar.png
- figures/operator_accuracy_by_category.png
- figures/latency_by_route.png
- figures/agent_time_breakdown.png
- figures/tokens_by_route.png
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import textwrap
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_operational_summary(path: Path) -> pd.DataFrame:
    """
    Loads the operational Summary.txt file directly.

    The real artifact may contain:
    - blank lines between records
    - the CSV header repeated before each record block

    This helper removes repeated headers and returns a clean DataFrame.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing operational summary file: {path}")

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Operational summary is empty: {path}")

    lines = [line for line in text.splitlines() if line.strip()]
    header = lines[0]
    filtered_lines = [header]

    for line in lines[1:]:
        if line == header:
            continue
        filtered_lines.append(line)

    reader = csv.DictReader(StringIO("\n".join(filtered_lines)))
    rows = list(reader)
    if not rows:
        raise ValueError(f"No operational rows found in summary: {path}")

    return pd.DataFrame(rows)


def get_metric(data: dict[str, Any], key: str, default: float | None = None) -> float | None:
    """
    Tries common aggregate locations:
    - root[key]
    - root["aggregate"][key]
    - root["global"][key]
    - root["metrics"][key]
    """
    candidates = [
        data,
        data.get("aggregate", {}),
        data.get("global", {}),
        data.get("metrics", {}),
    ]

    for candidate in candidates:
        if isinstance(candidate, dict) and key in candidate:
            value = candidate[key]
            if value is None:
                return default
            return float(value)

    return default


def short_route(route: str) -> str:
    route = str(route)

    mapping = {
        "operator>explainer": "Explainer",
        "operator>workout_editor>explainer": "Workout editor",
        "operator>nutrition_editor>explainer": "Nutrition editor",
        "operator>week_planner>explainer": "Week planner",
        "operator>librarian>workout_editor>explainer": "RAG + workout",
        "operator>workout_editor>nutrition_editor>explainer": "Workout + nutrition",
        "operator>librarian>workout_editor>nutrition_editor>explainer": "RAG + workout + nutrition",
    }

    return mapping.get(route, route.replace(">", " → "))


def wrap_labels(labels: list[str], width: int = 22) -> list[str]:
    return ["\n".join(textwrap.wrap(str(label), width=width)) for label in labels]


def save_bar(
    labels: list[str],
    values: list[float],
    ylabel: str,
    output_path: Path,
    rotate: int = 25,
) -> None:
    plt.figure(figsize=(10, 5))
    plt.bar(labels, values)
    plt.ylabel(ylabel)
    plt.ylim(0, max(1.0, max(values) * 1.15 if values else 1.0))
    plt.xticks(rotation=rotate, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_horizontal_bar(
    labels: list[str],
    values: list[float],
    xlabel: str,
    output_path: Path,
) -> None:
    plt.figure(figsize=(10, max(4, 0.55 * len(labels))))
    plt.barh(labels, values)
    plt.xlabel(xlabel)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


# ---------------------------------------------------------------------
# Experiment A plots
# ---------------------------------------------------------------------

def generate_phase_metrics_bar(exp_a_dir: Path, figures_dir: Path) -> None:
    """
    Generates:
    - figures/phase_metrics_bar.png

    Input:
    - exp_a_dir/aggregate_metrics.json
    """
    data = load_json(exp_a_dir / "aggregate_metrics.json")

    metrics = [
        ("SQL recall", "sql_candidate_recall_mean"),
        ("Vector Hit@3", "vector_hit_at_3_mean"),
        ("Vector nDCG@3", "vector_ndcg_at_3_mean"),
        ("Rerank Hit@3", "rerank_hit_at_3_mean"),
        ("Rerank nDCG@3", "rerank_ndcg_at_3_mean"),
    ]

    labels: list[str] = []
    values: list[float] = []

    for label, key in metrics:
        value = get_metric(data, key)
        if value is not None:
            labels.append(label)
            values.append(value)

    if not values:
        raise ValueError("No Experiment A aggregate metrics found for phase_metrics_bar.png")

    save_bar(
        labels=labels,
        values=values,
        ylabel="Valor",
        output_path=figures_dir / "phase_metrics_bar.png",
    )


def generate_rerank_position_relevance_heatmap(exp_a_dir: Path, figures_dir: Path) -> None:
    """
    Generates:
    - figures/rerank_position_relevance_heatmap.png

    Input:
    - exp_a_dir/reranked_results.csv

    Required columns:
    - rank
    - relevance_grade
    """
    path = exp_a_dir / "reranked_results.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing reranked results file: {path}")

    df = pd.read_csv(path)

    if "rank" not in df.columns or "relevance_grade" not in df.columns:
        raise ValueError("reranked_results.csv must contain columns: rank, relevance_grade")

    df = df.copy()
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["relevance_grade"] = pd.to_numeric(df["relevance_grade"], errors="coerce")
    df = df.dropna(subset=["rank", "relevance_grade"])

    df["rank"] = df["rank"].astype(int)
    df["relevance_grade"] = df["relevance_grade"].astype(int)

    ranks = [1, 2, 3]
    grades = [0, 1, 2, 3]

    heatmap = pd.crosstab(df["rank"], df["relevance_grade"])
    heatmap = heatmap.reindex(index=ranks, columns=grades, fill_value=0)

    colors = {
        0: "#4C78A8",
        1: "#F58518",
        2: "#54A24B",
        3: "#E45756",
    }
    labels = [f"Pos {rank}" for rank in ranks]
    x = list(range(len(ranks)))
    bottoms = [0] * len(ranks)

    plt.figure(figsize=(8, 4.5))
    for grade in grades:
        values = [int(heatmap.loc[rank, grade]) for rank in ranks]
        plt.bar(
            x,
            values,
            bottom=bottoms,
            color=colors[grade],
            label=f"Grado {grade}",
        )
        for idx, value in enumerate(values):
            if value > 0:
                plt.text(idx, bottoms[idx] + value / 2, str(value), ha="center", va="center", fontsize=9)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]

    plt.xticks(x, labels)
    plt.ylabel("Número de resultados")
    plt.legend(loc="upper right", title="Relevancia")
    plt.tight_layout()
    plt.savefig(figures_dir / "rerank_position_relevance_heatmap.png", dpi=300)
    plt.close()


# ---------------------------------------------------------------------
# Experiment B plots
# ---------------------------------------------------------------------

def generate_operator_overall_metrics_bar(exp_b_dir: Path, figures_dir: Path) -> None:
    """
    Generates:
    - figures/operator_overall_metrics_bar.png

    Input:
    - exp_b_dir/aggregate_metrics.json
    """
    data = load_json(exp_b_dir / "aggregate_metrics.json")

    metrics = [
        ("Exact plan", "exact_plan_accuracy"),
        ("Exact set", "exact_set_accuracy"),
        ("First agent", "first_agent_accuracy"),
        ("Non-empty plan", "non_empty_plan_rate"),
        ("All expected present", "all_expected_present_rate"),
        ("No unexpected agents", "no_unexpected_agents_rate"),
        ("Librarian order", "librarian_order_accuracy"),
    ]

    labels: list[str] = []
    values: list[float] = []

    for label, key in metrics:
        value = get_metric(data, key)
        if value is not None:
            labels.append(label)
            values.append(value)

    if not values:
        raise ValueError("No Experiment B aggregate metrics found for operator_overall_metrics_bar.png")

    save_bar(
        labels=wrap_labels(labels, width=16),
        values=values,
        ylabel="Valor",
        output_path=figures_dir / "operator_overall_metrics_bar.png",
        rotate=0,
    )


def generate_operator_accuracy_by_category(exp_b_dir: Path, figures_dir: Path) -> None:
    """
    Generates:
    - figures/operator_accuracy_by_category.png

    Input:
    - exp_b_dir/metrics_by_category.csv

    Expected columns:
    - category
    - exact_plan_accuracy
    """
    path = exp_b_dir / "metrics_by_category.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing category metrics file: {path}")

    df = pd.read_csv(path)

    if "category" not in df.columns:
        raise ValueError("metrics_by_category.csv must contain column: category")

    metric_col = None
    for candidate in ["exact_plan_accuracy", "exact_plan", "exact_plan_mean"]:
        if candidate in df.columns:
            metric_col = candidate
            break

    if metric_col is None:
        raise ValueError(
            "metrics_by_category.csv must contain one of: "
            "exact_plan_accuracy, exact_plan, exact_plan_mean"
        )

    df = df.copy()
    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce")
    df = df.dropna(subset=[metric_col])
    df = df.sort_values(metric_col, ascending=True)

    save_horizontal_bar(
        labels=wrap_labels(df["category"].astype(str).tolist(), width=28),
        values=df[metric_col].tolist(),
        xlabel="Exact plan accuracy",
        output_path=figures_dir / "operator_accuracy_by_category.png",
    )


# ---------------------------------------------------------------------
# Operational plots
# ---------------------------------------------------------------------

def generate_latency_by_route(operational_summary: Path, figures_dir: Path) -> None:
    """
    Generates:
    - figures/latency_by_route.png

    Input:
    - Summary.txt
    """
    df = load_operational_summary(operational_summary)

    required = {"route", "latency_s"}
    if not required.issubset(df.columns):
        raise ValueError(f"Operational CSV must contain columns: {required}")

    df = df.copy()
    df["latency_s"] = pd.to_numeric(df["latency_s"], errors="coerce")
    df = df.dropna(subset=["latency_s"])
    df["route_label"] = df["route"].apply(short_route)
    df = df.sort_values("latency_s", ascending=True)

    save_horizontal_bar(
        labels=wrap_labels(df["route_label"].tolist(), width=26),
        values=df["latency_s"].tolist(),
        xlabel="Segundos",
        output_path=figures_dir / "latency_by_route.png",
    )


def generate_tokens_by_route(operational_summary: Path, figures_dir: Path) -> None:
    """
    Generates:
    - figures/tokens_by_route.png

    Input:
    - Summary.txt
    """
    df = load_operational_summary(operational_summary)

    required = {"route", "total_tokens"}
    if not required.issubset(df.columns):
        raise ValueError(f"Operational CSV must contain columns: {required}")

    df = df.copy()
    df["total_tokens"] = pd.to_numeric(df["total_tokens"], errors="coerce")
    df = df.dropna(subset=["total_tokens"])
    df["route_label"] = df["route"].apply(short_route)
    df = df.sort_values("total_tokens", ascending=True)

    save_horizontal_bar(
        labels=wrap_labels(df["route_label"].tolist(), width=26),
        values=df["total_tokens"].tolist(),
        xlabel="Tokens",
        output_path=figures_dir / "tokens_by_route.png",
    )


def generate_agent_time_breakdown(operational_summary: Path, figures_dir: Path) -> None:
    """
    Generates:
    - figures/agent_time_breakdown.png

    Input:
    - Summary.txt

    This plot is a stacked horizontal bar chart showing how much each component
    contributed to total route latency.
    """
    df = load_operational_summary(operational_summary)

    agent_cols = [
        "operator_s",
        "librarian_s",
        "rag_s",
        "workout_editor_s",
        "nutrition_editor_s",
        "week_planner_s",
        "explainer_s",
    ]

    missing = [col for col in agent_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Operational CSV is missing agent duration columns: {missing}")

    if "route" not in df.columns or "latency_s" not in df.columns:
        raise ValueError("Operational CSV must contain columns: route, latency_s")

    df = df.copy()
    df["route_label"] = df["route"].apply(short_route)

    for col in agent_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["latency_s"] = pd.to_numeric(df["latency_s"], errors="coerce")
    df = df.dropna(subset=["latency_s"])
    df = df.sort_values("latency_s", ascending=True)

    readable = {
        "operator_s": "Operator",
        "librarian_s": "Librarian",
        "rag_s": "RAG",
        "workout_editor_s": "Workout editor",
        "nutrition_editor_s": "Nutrition editor",
        "week_planner_s": "Week planner",
        "explainer_s": "Explainer",
    }

    labels = wrap_labels(df["route_label"].tolist(), width=26)
    y_pos = list(range(len(df)))

    plt.figure(figsize=(11, max(5, 0.65 * len(df))))
    left = [0.0] * len(df)

    for col in agent_cols:
        values = df[col].tolist()

        if all(math.isclose(v, 0.0) for v in values):
            continue

        plt.barh(y_pos, values, left=left, label=readable[col])
        left = [l + v for l, v in zip(left, values)]

    plt.yticks(y_pos, labels)
    plt.xlabel("Segundos")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(figures_dir / "agent_time_breakdown.png", dpi=300)
    plt.close()


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate final TFG figures from existing evaluation outputs."
    )

    parser.add_argument(
        "--exp-a-dir",
        type=Path,
        required=True,
        help="Directory containing Experiment A outputs, e.g. evaluation_outputs/librarian_rag/20260606_120000",
    )

    parser.add_argument(
        "--exp-b-dir",
        type=Path,
        required=True,
        help="Directory containing Experiment B outputs, e.g. evaluation_outputs/operator_routing/20260606_130000",
    )

    parser.add_argument(
        "--operational-summary",
        type=Path,
        required=False,
        help="Path to Summary.txt with operational request metrics.",
    )

    parser.add_argument(
        "--operational-csv",
        type=Path,
        default=None,
        help="Deprecated alias for --operational-summary. Kept for backward compatibility.",
    )

    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=Path("figures"),
        help="Output directory for PNG figures. Default: figures",
    )

    args = parser.parse_args()
    operational_summary = args.operational_summary or args.operational_csv
    if operational_summary is None:
        parser.error("You must provide --operational-summary (or deprecated --operational-csv).")

    ensure_dir(args.figures_dir)

    print("Generating Experiment A figures...")
    generate_phase_metrics_bar(args.exp_a_dir, args.figures_dir)
    generate_rerank_position_relevance_heatmap(args.exp_a_dir, args.figures_dir)

    print("Generating Experiment B figures...")
    generate_operator_overall_metrics_bar(args.exp_b_dir, args.figures_dir)
    generate_operator_accuracy_by_category(args.exp_b_dir, args.figures_dir)

    print("Generating operational figures...")
    generate_latency_by_route(operational_summary, args.figures_dir)
    generate_agent_time_breakdown(operational_summary, args.figures_dir)
    generate_tokens_by_route(operational_summary, args.figures_dir)

    print(f"Done. Figures saved in: {args.figures_dir.resolve()}")


if __name__ == "__main__":
    main()
