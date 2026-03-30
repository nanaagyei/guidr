"""Script to start the backend server."""

import logging
import uvicorn

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Apply pending Alembic migrations before accepting traffic."""
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as exc:
        logger.warning("Could not run Alembic migrations automatically: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _run_migrations()

    from src.main import app

    uvicorn.run(app, host="0.0.0.0", port=8000)
