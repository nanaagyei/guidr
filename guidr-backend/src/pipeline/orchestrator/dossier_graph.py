"""LangGraph dossier orchestrator: research → validate → score → stage → promote."""
from __future__ import annotations

import logging
from typing import Literal

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    StateGraph = None
    END = None
    MemorySaver = None

from src.pipeline.orchestrator.dossier_state import DossierState
from src.pipeline.orchestrator.dossier_nodes import (
    load_dossier_context,
    research_extract,
    validate_citations,
    score_dossier_confidence,
    stage_dossier,
    fallback_scrape,
    promote_dossier,
)

logger = logging.getLogger(__name__)


def confidence_decision(state: DossierState) -> Literal["stage_promote", "stage_only", "fallback", "stage_low"]:
    """Route based on confidence score."""
    confidence = state.get("confidence", 0.0)
    needs_fallback = state.get("needs_fallback", False)

    from src.config import settings

    if confidence >= 0.85:
        return "stage_promote"
    if confidence >= 0.70:
        return "stage_only"
    if needs_fallback and settings.enable_scrape_fallback:
        return "fallback"
    return "stage_low"


def create_dossier_graph(checkpointer=None):
    """Build and compile the dossier orchestrator graph."""
    if StateGraph is None:
        raise ImportError("langgraph not installed. Run: pip install langgraph")

    graph = StateGraph(DossierState)

    graph.add_node("load_dossier_context", load_dossier_context)
    graph.add_node("research_extract", research_extract)
    graph.add_node("validate_citations", validate_citations)
    graph.add_node("score_dossier_confidence", score_dossier_confidence)
    graph.add_node("stage_dossier", stage_dossier)
    graph.add_node("fallback_scrape", fallback_scrape)
    graph.add_node("rescore", score_dossier_confidence)  # re-use same node after fallback
    graph.add_node("stage_after_fallback", stage_dossier)
    graph.add_node("promote_dossier", promote_dossier)

    graph.set_entry_point("load_dossier_context")
    graph.add_edge("load_dossier_context", "research_extract")
    graph.add_edge("research_extract", "validate_citations")
    graph.add_edge("validate_citations", "score_dossier_confidence")

    graph.add_conditional_edges(
        "score_dossier_confidence",
        confidence_decision,
        {
            "stage_promote": "stage_dossier",
            "stage_only": "stage_dossier",
            "fallback": "fallback_scrape",
            "stage_low": "stage_dossier",
        },
    )

    # After staging, promote if confidence is high enough OR if this is a recommendation run
    # (recommendations always need to be promoted so users see results)
    graph.add_conditional_edges(
        "stage_dossier",
        lambda s: "promote" if (
            s.get("promote", False) or s.get("job_type") == "recommendation_run"
        ) else "end",
        {"promote": "promote_dossier", "end": END},
    )

    # Fallback flow: scrape → re-score → stage → maybe promote
    graph.add_edge("fallback_scrape", "rescore")
    graph.add_edge("rescore", "stage_after_fallback")
    graph.add_conditional_edges(
        "stage_after_fallback",
        lambda s: "promote" if (
            s.get("confidence", 0) >= 0.85 or s.get("job_type") == "recommendation_run"
        ) else "end",
        {"promote": "promote_dossier", "end": END},
    )

    graph.add_edge("promote_dossier", END)

    compiled = graph.compile(
        checkpointer=checkpointer or (MemorySaver() if MemorySaver else None)
    )
    return compiled
