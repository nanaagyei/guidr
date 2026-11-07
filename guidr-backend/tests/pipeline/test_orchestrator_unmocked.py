"""Run the real enrichment and dossier graph paths against Postgres (#57).

Only the network is mocked: the page fetch (Firecrawl), object storage, the per-domain
rate limiter and domain-health circuit breaker. Nodes, routing and the
``ConfidenceScorer`` are real, and rows are written to a real, migrated database.

Skipped unless ``DATABASE_URL`` points at a reachable Postgres on which
``alembic upgrade head`` has run (``tests/pipeline/conftest.py`` mocks ``src.db``, so this
module builds its own engine).
"""
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

OVERVIEW_PAGE = """# Example University

Example University is a private research university founded in 1890, known for its graduate \
programs in engineering, the sciences and the humanities, and for a collaborative research culture.

## Facts
- Acceptance rate: 12%
- Total enrollment: 15,000 students
- Graduate enrollment: 6,500 students
- Campus setting: urban campus in a major city
- Academic calendar: semester system
"""


@pytest.fixture
def session_factory():
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker

    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs DATABASE_URL pointing at Postgres")
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    except Exception:
        pytest.skip("database not reachable")
    if not {"raw_artifacts", "source_documents", "entity_promotions"} <= tables:
        pytest.skip("needs a migrated database (alembic upgrade head)")
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture
def institution(session_factory):
    from src.models.institution import Institution

    db = session_factory()
    inst = Institution(
        id=uuid.uuid4(),
        name=f"Example University {uuid.uuid4().hex[:6]}",
        country="US",
        website_url=f"https://{uuid.uuid4().hex[:8]}.example.edu",
    )
    db.add(inst)
    db.commit()
    inst_id, website = inst.id, inst.website_url
    db.close()
    yield inst_id, website
    _cleanup(session_factory, inst_id)


def _cleanup(session_factory, inst_id):
    from src.models.confidence_score import ConfidenceScore
    from src.models.enrichment_cache import EnrichmentCache
    from src.models.entity_promotion import EntityPromotion
    from src.models.extraction_run import ExtractionRun
    from src.models.institution import Institution
    from src.models.raw_artifact import RawArtifact
    from src.models.source_document import SourceDocument
    from src.models.validation_report import ValidationReport

    db = session_factory()
    run_ids = [r.id for r in db.query(ExtractionRun).filter(ExtractionRun.entity_id == inst_id)]
    artifact_ids = [
        r.raw_artifact_id
        for r in db.query(ExtractionRun).filter(ExtractionRun.entity_id == inst_id)
    ]
    db.query(EntityPromotion).filter(EntityPromotion.entity_id == inst_id).delete()
    db.query(ConfidenceScore).filter(ConfidenceScore.entity_id == inst_id).delete()
    db.query(ValidationReport).filter(ValidationReport.entity_id == inst_id).delete()
    db.query(EnrichmentCache).filter(EnrichmentCache.entity_id == inst_id).delete()
    if run_ids:
        db.query(ExtractionRun).filter(ExtractionRun.id.in_(run_ids)).delete()
    if artifact_ids:
        db.query(RawArtifact).filter(RawArtifact.id.in_(artifact_ids)).delete()
    db.query(SourceDocument).filter(SourceDocument.entity_id == inst_id).delete()
    db.query(Institution).filter(Institution.id == inst_id).delete()
    db.commit()
    db.close()


def _network_mocks(page_markdown):
    firecrawl = MagicMock()
    firecrawl.return_value.scrape_url.return_value = {
        "markdown": page_markdown,
        "metadata": {"statusCode": 200},
    }
    storage = MagicMock()
    storage.return_value.store_text.return_value = "raw/school/page.md"
    health = MagicMock()
    health.return_value.is_blocked.return_value = False
    token = MagicMock(return_value=MagicMock(allowed=True))
    return [
        patch("src.pipeline.clients.EnhancedFirecrawlClient", firecrawl),
        patch("src.pipeline.clients.DataLakeStorageClient", storage),
        patch("src.pipeline.services.domain_health_service.DomainHealthService", health),
        patch("src.pipeline.redis_keyspace.take_token_for_url", token),
    ]


def test_enrichment_graph_fetch_to_promote(session_factory, institution):
    from src.models.confidence_score import ConfidenceScore
    from src.models.entity_promotion import EntityPromotion
    from src.models.extraction_run import ExtractionRun
    from src.models.institution import Institution
    from src.models.raw_artifact import RawArtifact
    from src.models.source_document import SourceDocument
    from src.pipeline.orchestrator.graph import create_orchestrator_graph

    inst_id, website = institution
    mocks = _network_mocks(OVERVIEW_PAGE)
    for m in mocks:
        m.start()
    try:
        with patch("src.pipeline.orchestrator.nodes._get_db", side_effect=session_factory):
            graph = create_orchestrator_graph()
            result = graph.invoke(
                {
                    "job_id": str(uuid.uuid4()),
                    "entity_kind": "school",
                    "entity_id": str(inst_id),
                    "category": "SCHOOL_OVERVIEW",
                    "retry_count": 0,
                    "max_attempts": 3,
                    "progress": [],
                },
                config={"configurable": {"thread_id": str(uuid.uuid4())}},
            )
    finally:
        for m in mocks:
            m.stop()

    assert result["progress"][-2:] == ["stage_write", "promote_write"], result["progress"]
    assert result["confidence"] >= 0.78
    assert result.get("status") == "success"

    db = session_factory()
    try:
        run = db.query(ExtractionRun).filter(ExtractionRun.entity_id == inst_id).one()
        artifact = db.query(RawArtifact).filter(RawArtifact.id == run.raw_artifact_id).one()
        source = db.query(SourceDocument).filter(
            SourceDocument.id == artifact.source_document_id
        ).one()
        assert source.canonical_url == website
        assert source.entity_id == inst_id

        score = db.query(ConfidenceScore).filter(ConfidenceScore.extraction_run_id == run.id).one()
        for sub in ("source_score", "extraction_score", "validation_score", "staleness_score"):
            assert getattr(score, sub) is not None, sub

        promotion = db.query(EntityPromotion).filter(
            EntityPromotion.extraction_run_id == run.id
        ).one()
        assert promotion.entity_id == inst_id

        inst = db.query(Institution).filter(Institution.id == inst_id).one()
        assert inst.enrollment_total == 15000
    finally:
        db.close()


def test_low_confidence_result_is_staged_not_promoted(session_factory, institution):
    """A thin page is still recorded (staged) but not promoted."""
    from src.models.entity_promotion import EntityPromotion
    from src.models.extraction_run import ExtractionRun
    from src.pipeline.orchestrator.graph import create_orchestrator_graph

    inst_id, _ = institution
    thin_page = (
        "Example University offers graduate programs across many departments and research "
        "centres, with an emphasis on interdisciplinary work and close faculty mentoring."
    )
    mocks = _network_mocks(thin_page)
    for m in mocks:
        m.start()
    try:
        with patch("src.pipeline.orchestrator.nodes._get_db", side_effect=session_factory):
            result = create_orchestrator_graph().invoke(
                {
                    "entity_kind": "school",
                    "entity_id": str(inst_id),
                    "category": "SCHOOL_OVERVIEW",
                    # Off-domain source keeps the score below the promotion threshold
                    "website_hint": "https://other-site.example.com",
                    "retry_count": 0,
                    "max_attempts": 3,
                    "progress": [],
                },
                config={"configurable": {"thread_id": str(uuid.uuid4())}},
            )
    finally:
        for m in mocks:
            m.stop()

    assert result["confidence"] < 0.78
    assert result["progress"][-1] == "stage_write"
    db = session_factory()
    try:
        run = db.query(ExtractionRun).filter(ExtractionRun.entity_id == inst_id).one()
        assert run.status == "draft"
        assert db.query(EntityPromotion).filter(EntityPromotion.entity_id == inst_id).count() == 0
    finally:
        db.close()


def test_school_dossier_promotion_leaves_audit_row(session_factory, institution):
    """stage_dossier records provenance; promote_dossier links its audit row to it."""
    from src.models.entity_promotion import EntityPromotion
    from src.models.extraction_run import ExtractionRun
    from src.models.institution import Institution
    from src.pipeline.orchestrator import dossier_nodes

    inst_id, _ = institution
    dossier_json = {
        "overview": {
            "description": "A research university.",
            "campus_setting": "urban",
            "total_enrollment": 21000,
            "grad_enrollment": 9000,
            "acceptance_rate": 0.1,
            "academic_calendar": "quarter",
        }
    }
    state = {
        "entity_kind": "school",
        "entity_id": str(inst_id),
        "job_type": "school_dossier",
        "dossier_json": dossier_json,
        "dossier_citations": [{"id": "c1", "url": "https://example.edu/about"}],
        "dossier_evidence_map": {},
        "confidence": 0.9,
        "promote": True,
        "progress": [],
    }
    with patch.object(dossier_nodes, "_get_db", side_effect=session_factory), \
         patch("src.pipeline.orchestrator.nodes._get_db", side_effect=session_factory):
        staged = dossier_nodes.stage_dossier(state)
        assert staged["extraction_run_id"]
        dossier_nodes.promote_dossier({**state, **staged})

    db = session_factory()
    try:
        run = db.query(ExtractionRun).filter(
            ExtractionRun.id == uuid.UUID(staged["extraction_run_id"])
        ).one()
        assert run.extractor_name == "research_gateway:school_dossier"
        promotion = db.query(EntityPromotion).filter(
            EntityPromotion.extraction_run_id == run.id
        ).one()
        assert "enrollment_total" in promotion.diff_json
        inst = db.query(Institution).filter(Institution.id == inst_id).one()
        assert inst.enrollment_total == 21000
        assert inst.campus_setting == "urban"
    finally:
        db.close()


@pytest.mark.parametrize(
    "source,expected",
    [
        ("perplexity_sonar", "perplexity"),
        ("perplexity_citation", "perplexity"),
        ("open_deep_research", "open_deep_research"),
        ("perplexity_stub", "manual"),
        (None, "manual"),
        ("manual", "manual"),
    ],
)
def test_research_provider_label_matches_enum(source, expected):
    from src.models.source_document import RESEARCH_PROVIDERS, research_provider_label

    label = research_provider_label(source)
    assert label == expected
    assert label in RESEARCH_PROVIDERS


def test_discovered_urls_are_persisted(session_factory, institution):
    """URLs from the research gateway land in source_documents (enum-safe provider label)."""
    from src.models.source_document import SourceDocument
    from src.pipeline.orchestrator import nodes
    from src.pipeline.research_gateway.schemas import URLDiscoveryResult

    inst_id, _ = institution
    response = MagicMock()
    response.results = [
        URLDiscoveryResult(url="https://grad.example.edu/admissions", source="perplexity_sonar"),
    ]
    with patch.object(nodes, "_get_db", side_effect=session_factory), \
         patch.object(nodes, "ResearchGatewayService") as svc:
        svc.return_value.run.return_value = response
        nodes.discover_urls(
            {"entity_kind": "school", "entity_id": str(inst_id), "entity_name": "Example",
             "category": "SCHOOL_OVERVIEW", "progress": []}
        )

    db = session_factory()
    try:
        doc = db.query(SourceDocument).filter(SourceDocument.entity_id == inst_id).one()
        assert doc.discovered_by == "perplexity"
        assert doc.host == "grad.example.edu"  # generated column filled by Postgres
    finally:
        db.close()
