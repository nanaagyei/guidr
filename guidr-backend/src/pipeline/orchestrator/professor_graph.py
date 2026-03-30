"""LangGraph professor match orchestrator: OpenAlex → S2 enrich → synthesize → stage → promote."""
from __future__ import annotations

import logging

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    StateGraph = None
    END = None
    MemorySaver = None

from src.pipeline.orchestrator.professor_state import ProfessorMatchState
from src.pipeline.orchestrator.professor_nodes import (
    load_professor_context,
    query_openalex,
    enrich_semantic_scholar,
    synthesize_rank,
    stage_professor_matches,
    promote_professor_matches,
)

logger = logging.getLogger(__name__)


def create_professor_match_graph(checkpointer=None):
    """Build and compile the professor match graph.

    Linear flow:
        load_professor_context → query_openalex → enrich_semantic_scholar
        → synthesize_rank → stage_professor_matches → promote_professor_matches → END
    """
    if StateGraph is None:
        raise ImportError("langgraph not installed. Run: pip install langgraph")

    graph = StateGraph(ProfessorMatchState)

    graph.add_node("load_professor_context", load_professor_context)
    graph.add_node("query_openalex", query_openalex)
    graph.add_node("enrich_semantic_scholar", enrich_semantic_scholar)
    graph.add_node("synthesize_rank", synthesize_rank)
    graph.add_node("stage_professor_matches", stage_professor_matches)
    graph.add_node("promote_professor_matches", promote_professor_matches)

    graph.set_entry_point("load_professor_context")
    graph.add_edge("load_professor_context", "query_openalex")
    graph.add_edge("query_openalex", "enrich_semantic_scholar")
    graph.add_edge("enrich_semantic_scholar", "synthesize_rank")
    graph.add_edge("synthesize_rank", "stage_professor_matches")
    graph.add_edge("stage_professor_matches", "promote_professor_matches")
    graph.add_edge("promote_professor_matches", END)

    compiled = graph.compile(
        checkpointer=checkpointer or (MemorySaver() if MemorySaver else None)
    )
    return compiled
