from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import KfcAppInstallsSnapshot
from app.service import DashboardUnavailable, get_dashboard


class FakeSettings:
    cache_ttl_seconds = 900
    app_timezone = "America/Guayaquil"
    windsor_api_key = None


def session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def test_windsor_failure_returns_snapshot_when_available() -> None:
    SessionLocal = session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    db.add(
        KfcAppInstallsSnapshot(
            from_date=date(2025, 12, 29),
            to_date=date(2026, 1, 4),
            source_updated_at=now,
            payload_json={
                "dashboardId": "kfc-app-installs",
                "title": "KFC Instalaciones App",
                "brand": "KFC",
                "isMock": False,
                "source": "windsor",
                "updatedAt": "2026-01-04T12:00:00Z",
                "from": "2025-12-29",
                "to": "2026-01-04",
                "shareToken": None,
                "weeks": [],
            },
        )
    )
    db.commit()

    payload = get_dashboard(
        db,
        FakeSettings(),
        from_date=date(2025, 12, 29),
        to_date=date(2026, 1, 4),
        force_refresh=True,
    )

    assert payload["source"] == "snapshot"
    assert payload["stale"] is True
    assert payload["weeks"] == []


def test_windsor_failure_without_snapshot_raises_unavailable() -> None:
    SessionLocal = session_factory()
    db = SessionLocal()

    with pytest.raises(DashboardUnavailable):
        get_dashboard(
            db,
            FakeSettings(),
            from_date=date(2025, 12, 29),
            to_date=date(2026, 1, 4),
            force_refresh=True,
        )
