"""Domain health tracking service for scraping reliability."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.db import SessionLocal
from src.models.domain_health import DomainHealth
from src.pipeline.redis_keyspace.rate_limit import (
    check_circuit_breaker,
    record_domain_error as redis_record_error,
    record_domain_success as redis_record_success,
)

logger = logging.getLogger(__name__)

# After this many consecutive errors the domain is considered problematic
ERROR_STREAK_BLOCK_THRESHOLD = 10

# How long to block a domain after it exceeds the streak threshold
BLOCK_COOLDOWN_HOURS = 24

# How long before a blocked domain auto-resets
BLOCK_RESET_DAYS = 7


class DomainHealthService:
    """Manages per-domain health state in both Redis (fast path) and Postgres (durable)."""

    def record_success(self, host: str) -> None:
        """Record a successful request to a domain."""
        # Fast path: clear Redis circuit breaker streak
        try:
            redis_record_success(host)
        except Exception:
            pass

        # Durable path: update Postgres
        db = SessionLocal()
        try:
            row = db.query(DomainHealth).filter(DomainHealth.host == host).first()
            if row is None:
                row = DomainHealth(host=host, error_streak=0)
                db.add(row)
            row.last_ok_at = datetime.utcnow()
            row.error_streak = 0
            row.block_detected = False
            row.next_allowed_at = None
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.debug("domain_health record_success failed: %s", exc)
        finally:
            db.close()

    def record_error(self, host: str, http_status: Optional[int] = None) -> int:
        """Record a failed request. Returns updated error streak count."""
        # Fast path: Redis circuit breaker
        try:
            redis_record_error(host)
        except Exception:
            pass

        # Durable path: Postgres
        db = SessionLocal()
        try:
            row = db.query(DomainHealth).filter(DomainHealth.host == host).first()
            if row is None:
                row = DomainHealth(host=host, error_streak=0)
                db.add(row)

            row.error_streak = (row.error_streak or 0) + 1
            row.last_error_at = datetime.utcnow()

            if http_status:
                row.notes = f"Last HTTP status: {http_status}"

            # Block if streak exceeds threshold
            if row.error_streak >= ERROR_STREAK_BLOCK_THRESHOLD:
                row.block_detected = True
                row.next_allowed_at = datetime.utcnow() + timedelta(hours=BLOCK_COOLDOWN_HOURS)
                logger.warning(
                    "Domain %s blocked: %d consecutive errors", host, row.error_streak
                )

            db.commit()
            return row.error_streak
        except Exception as exc:
            db.rollback()
            logger.debug("domain_health record_error failed: %s", exc)
            return 0
        finally:
            db.close()

    def is_blocked(self, host: str) -> bool:
        """Check if a domain is currently blocked (Redis fast path + Postgres fallback)."""
        # Check Redis circuit breaker first (fast)
        try:
            if check_circuit_breaker(host):
                return True
        except Exception:
            pass

        # Fallback to Postgres
        db = SessionLocal()
        try:
            row = db.query(DomainHealth).filter(DomainHealth.host == host).first()
            if row is None:
                return False
            if not row.block_detected:
                return False
            # Check if cooldown has expired
            if row.next_allowed_at and row.next_allowed_at <= datetime.utcnow():
                return False
            return True
        except Exception as exc:
            logger.debug("domain_health is_blocked failed: %s", exc)
            return False
        finally:
            db.close()

    def get_all_health(self, db: Optional[Session] = None) -> list[dict]:
        """Get health overview for all tracked domains (admin endpoint)."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            rows = (
                db.query(DomainHealth)
                .order_by(DomainHealth.error_streak.desc())
                .limit(200)
                .all()
            )
            return [
                {
                    "host": r.host,
                    "last_ok_at": r.last_ok_at.isoformat() if r.last_ok_at else None,
                    "last_error_at": r.last_error_at.isoformat() if r.last_error_at else None,
                    "error_streak": r.error_streak,
                    "block_detected": r.block_detected,
                    "next_allowed_at": (
                        r.next_allowed_at.isoformat() if r.next_allowed_at else None
                    ),
                    "notes": r.notes,
                }
                for r in rows
            ]
        except Exception as exc:
            logger.debug("domain_health get_all_health failed: %s", exc)
            return []
        finally:
            if close_db:
                db.close()

    def reset_stale_blocks(self, older_than_days: int = BLOCK_RESET_DAYS) -> int:
        """Reset blocked domains whose cooldown expired more than N days ago.

        Returns the number of domains reset.
        """
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        db = SessionLocal()
        try:
            count = (
                db.query(DomainHealth)
                .filter(
                    DomainHealth.block_detected.is_(True),
                    DomainHealth.next_allowed_at <= cutoff,
                )
                .update(
                    {
                        DomainHealth.block_detected: False,
                        DomainHealth.error_streak: 0,
                        DomainHealth.next_allowed_at: None,
                        DomainHealth.notes: "Auto-reset by maintenance",
                    },
                    synchronize_session=False,
                )
            )
            db.commit()
            logger.info("Reset %d stale domain blocks", count)
            return count
        except Exception as exc:
            db.rollback()
            logger.debug("domain_health reset_stale_blocks failed: %s", exc)
            return 0
        finally:
            db.close()
