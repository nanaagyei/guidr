"""Conftest for pipeline tests: mock heavy dependencies to avoid import failures.

Mocks src.db (psycopg2), pgvector, and celery before any test imports trigger them.
"""
import sys
import types
from unittest.mock import MagicMock
from sqlalchemy.orm import declarative_base

# ── Mock pgvector (not installed in test env) ────────────────────────
if "pgvector" not in sys.modules:
    pgvector_mod = types.ModuleType("pgvector")
    pgvector_sa = types.ModuleType("pgvector.sqlalchemy")
    pgvector_sa.Vector = MagicMock()
    pgvector_mod.sqlalchemy = pgvector_sa
    sys.modules["pgvector"] = pgvector_mod
    sys.modules["pgvector.sqlalchemy"] = pgvector_sa

# ── Mock celery (not installed in test env) ──────────────────────────
if "celery" not in sys.modules:
    celery_mod = types.ModuleType("celery")
    celery_mod.Celery = MagicMock()

    # shared_task: return the function unchanged (acts as no-op decorator)
    def _shared_task(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f

    celery_mod.shared_task = _shared_task
    celery_mod.chain = MagicMock()
    celery_mod.group = MagicMock()

    celery_schedules = types.ModuleType("celery.schedules")
    celery_schedules.crontab = MagicMock()

    sys.modules["celery"] = celery_mod
    sys.modules["celery.schedules"] = celery_schedules

# ── Mock src.db (avoids psycopg2 create_engine at import time) ───────
if "src.db" not in sys.modules:
    mock_db_module = types.ModuleType("src.db")
    mock_db_module.Base = declarative_base()
    mock_db_module.SessionLocal = MagicMock()
    mock_db_module.engine = MagicMock()
    mock_db_module.get_db = MagicMock()
    sys.modules["src.db"] = mock_db_module
