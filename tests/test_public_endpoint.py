from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import KfcAppInstallsShare, KfcAppInstallsSnapshot


def test_public_endpoint_does_not_expose_private_fields() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)
    db.add(
        KfcAppInstallsShare(
            share_token="public-token",
            shared_at=now,
            created_by_oid="private-oid",
            created_by_email="private@example.com",
        )
    )
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
                "shareToken": "public-token",
                "sourceError": "private detail",
                "weeks": [],
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
        client = TestClient(app)
        response = client.get(
            "/api/public/kfc-app-installs/public-token",
            params={"from": "2025-12-29", "to": "2026-01-04"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "shareToken" not in payload
    assert payload["isMock"] is False
    assert "sourceError" not in payload
    assert "rawRows" not in payload
    assert payload["weeks"] == []


def test_revoked_public_token_returns_404() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)
    db.add(
        KfcAppInstallsShare(
            share_token="revoked-token",
            shared_at=now,
            revoked_at=now,
            created_by_oid="private-oid",
            created_by_email="private@example.com",
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
        client = TestClient(app)
        response = client.get("/api/public/kfc-app-installs/revoked-token")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
