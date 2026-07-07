from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import KfcAppInstallsSnapshot
from app.security import AuthUser, get_current_user


class FakeSettings:
    auth_disabled = False
    auth_disabled_token = "local-dev-admin"
    azure_jwks_url = "https://login.example.test/keys"
    azure_client_ids = ["client-id"]
    azure_issuer = "https://login.example.test/tenant/v2.0"
    auth_jwks_timeout_seconds = 1
    allowed_role_set = {"planners", "admin"}
    cache_ttl_seconds = 900
    app_timezone = "America/Guayaquil"
    windsor_api_key = None


def test_dashboard_without_token_returns_401_before_db() -> None:
    def fail_db():
        raise AssertionError("DB dependency should not run before auth")
        yield

    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_db] = fail_db
    try:
        response = TestClient(app).get("/api/kfc-app-installs/dashboard")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_dashboard_invalid_token_returns_401_before_db() -> None:
    def fail_db():
        raise AssertionError("DB dependency should not run before auth")
        yield

    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_db] = fail_db
    try:
        response = TestClient(app).get(
            "/api/kfc-app-installs/dashboard",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_dashboard_valid_token_without_role_returns_403_before_db() -> None:
    def fail_db():
        raise AssertionError("DB dependency should not run before role check")
        yield

    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        oid="user",
        email="user@example.com",
        roles={"Viewer"},
        claims={},
    )
    app.dependency_overrides[get_db] = fail_db
    try:
        response = TestClient(app).get(
            "/api/kfc-app-installs/dashboard",
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.parametrize("role", ["Planners", "admin"])
def test_dashboard_valid_role_reads_snapshot(role: str) -> None:
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
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        oid="user",
        email="user@example.com",
        roles={role},
        claims={},
    )
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get(
            "/api/kfc-app-installs/dashboard",
            params={"from": "2025-12-29", "to": "2026-01-04"},
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["dashboardId"] == "kfc-app-installs"
