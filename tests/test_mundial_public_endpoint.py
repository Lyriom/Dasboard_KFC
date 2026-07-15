from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import KfcMundialShare, KfcMundialSnapshot


def test_mundial_public_endpoint_returns_public_token_not_share_token() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    db.add(
        KfcMundialShare(
            share_token="mundial-public-token",
            shared_at=now,
            created_by_oid="private-oid",
            created_by_email="private@example.com",
        )
    )
    db.add(
        KfcMundialSnapshot(
            from_date=date(2026, 6, 11),
            to_date=date(2026, 6, 11),
            source_updated_at=now,
            payload_json={
                "dashboardId": "kfc-mundial",
                "title": "Mundial Heavy Up · KFC App",
                "brand": "KFC",
                "isMock": False,
                "source": "windsor",
                "updatedAt": "2026-07-13T22:00:00.000Z",
                "from": "2026-06-11",
                "to": "2026-06-11",
                "days": ["2026-06-11"],
                "meta": {},
                "google": {"DOM": [], "EXP": []},
                "googleDays": [],
                "ventas": {},
                "matchDays": [],
                "ecuDays": [],
                "matchDaysG": [],
                "ecuDaysG": [],
                "rules": {},
                "shareToken": "mundial-public-token",
                "publicToken": None,
                "sourceError": "private detail",
                "rawRows": [{"api_key": "secret"}],
            },
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get(
            "/api/public/kfc-mundial/mundial-public-token",
            params={"from": "2026-06-11", "to": "2026-06-11"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboardId"] == "kfc-mundial"
    assert payload["publicToken"] == "mundial-public-token"
    assert "shareToken" not in payload
    assert "sourceError" not in payload
    assert "rawRows" not in payload
