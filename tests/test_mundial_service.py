from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import KfcMundialSnapshot
from app.mundial_service import refresh_mundial_dashboard
from app.windsor import WindsorError


class FakeSettings:
    app_timezone = "America/Guayaquil"
    cache_ttl_seconds = 900
    windsor_api_key = "fake-key"
    windsor_base_url = "https://connectors.windsor.ai"
    http_timeout_seconds = 60
    http_retries = 3


class PartialWindsorClient:
    base_url = "https://connectors.windsor.ai"

    def __init__(self, settings):
        self.settings = settings

    def fetch_connector(self, connector, fields, date_from, date_to):
        if connector == "facebook":
            return [
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_KFC_META_HEAVY UP_MUNDIAL APP_ADQUISICION",
                    "adset_name": "ADQUISICION DOMICILIO CUARTOS",
                    "spend": "10",
                    "actions_omni_purchase": "1",
                    "action_values_omni_purchase": "20",
                }
            ]
        if connector == "googleanalytics4":
            return []
        raise WindsorError("HTTP 400 body={\"error\":\"bad field\"}")


def test_refresh_mundial_dashboard_saves_partial_snapshot(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    monkeypatch.setattr("app.mundial_service.WindsorClient", PartialWindsorClient)

    payload = refresh_mundial_dashboard(
        db,
        FakeSettings(),
        from_date=date(2026, 6, 11),
        to_date=date(2026, 6, 11),
    )

    snapshot = db.query(KfcMundialSnapshot).one()
    assert snapshot.payload_json["dashboardId"] == "kfc-mundial"
    assert payload["dashboardId"] == "kfc-mundial"
    assert payload["meta"]["heavyUp"]["ADQ|DOM"]["sp"] == [10.0]
    assert payload["google"]["DOM"][0][:5] == ["11 jun", "UAC", 209, 120, 89]
    assert payload["google"]["DOM"][0][9] == 0.0
    assert "sourceError" in payload
    assert "google_ads failed with primary and fallback fields" in payload["sourceError"]
