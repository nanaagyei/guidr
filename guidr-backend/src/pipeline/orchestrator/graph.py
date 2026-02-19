"""LangGraph orchestrator: discovery -> fetch -> extract -> validate -> promote."""
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

from src.pipeline.orchestrator.state import OrchestratorState
from src.pipeline.orchestrator.nodes import (
    load_context,
    discover_urls,
    repair_extraction,
    canonicalize_urls,
    fetch_page,
    store_raw,
    extract_structured,
    validate_payload,
    score_confidence,
    stage_write,
    promote_write,
    retry_backoff,
    fail_final,
)

logger = logging.getLogger(__name__)


def need_discovery(state: OrchestratorState) -> Literal["discover", "fetch"]:
    """Route: discovery vs direct fetch."""
    if state.get("need_discovery", True):
        return "discover"
    return "fetch"


def promote_decision(state: OrchestratorState) -> Literal["promote", "repair", "retry"]:
    """Route: promote, repair, or retry."""
    if state.get("promote", False):
        return "promote"
    if state.get("repair", False):
        return "repair"
    return "retry"


def stage_decision(state: OrchestratorState) -> Literal["promote_write", "end"]:
    """After staging, decide whether to also promote to production."""
    confidence = state.get("confidence", 0.0)
    from src.pipeline.processors.confidence_scorer import AUTO_PROMOTE_THRESHOLD
    if confidence >= AUTO_PROMOTE_THRESHOLD and state.get("promote", False):
        return "promote_write"
    return "end"


def create_orchestrator_graph(checkpointer=None):
    """Build and compile the orchestrator graph."""
    if StateGraph is None:
        raise ImportError("langgraph not installed. Run: pip install langgraph")
    graph = StateGraph(OrchestratorState)

    graph.add_node("load_context", load_context)
    graph.add_node("discover_urls", discover_urls)
    graph.add_node("repair", repair_extraction)
    graph.add_node("canonicalize_urls", canonicalize_urls)
    graph.add_node("fetch_page", fetch_page)
    graph.add_node("store_raw", store_raw)
    graph.add_node("extract_structured", extract_structured)
    graph.add_node("validate", validate_payload)
    graph.add_node("score_confidence", score_confidence)
    graph.add_node("stage_write", stage_write)
    graph.add_node("promote_write", promote_write)
    graph.add_node("retry_backoff", retry_backoff)
    graph.add_node("fail_final", fail_final)

    graph.set_entry_point("load_context")
    graph.add_conditional_edges("load_context", need_discovery, {"discover": "discover_urls", "fetch": "canonicalize_urls"})
    graph.add_edge("discover_urls", "canonicalize_urls")
    graph.add_edge("repair", "canonicalize_urls")
    graph.add_edge("canonicalize_urls", "fetch_page")
    graph.add_edge("fetch_page", "store_raw")
    graph.add_edge("store_raw", "extract_structured")
    graph.add_edge("extract_structured", "validate")
    graph.add_edge("validate", "score_confidence")
    graph.add_conditional_edges(
        "score_confidence",
        promote_decision,
        {"promote": "stage_write", "repair": "repair", "retry": "retry_backoff"},
    )
    # After staging, conditionally promote or end
    graph.add_conditional_edges(
        "stage_write",
        stage_decision,
        {"promote_write": "promote_write", "end": END},
    )
    graph.add_edge("promote_write", END)
    graph.add_edge("retry_backoff", END)
    graph.add_edge("fail_final", END)

    compiled = graph.compile(checkpointer=checkpointer or (MemorySaver() if MemorySaver else None))
    return compiled
