from __future__ import annotations

from app.aggregation import normalize_google, normalize_tiktok
from app.constants import GOOGLE_CAMPAIGN_EXACT


def test_google_uses_biddable_app_install_conversions_only() -> None:
    row = {
        "date": "2026-06-01",
        "account_id": "697-583-7337",
        "campaign": GOOGLE_CAMPAIGN_EXACT,
        "spend": "100",
        "biddable_app_install_conversions": "4",
        "conversions": "999",
    }

    normalized = normalize_google(row)

    assert normalized is not None
    assert normalized.installs == 4


def test_google_does_not_fallback_to_conversions() -> None:
    row = {
        "date": "2026-06-01",
        "account_id": "6975837337",
        "campaign": GOOGLE_CAMPAIGN_EXACT,
        "spend": "100",
        "conversions": "999",
    }

    normalized = normalize_google(row)

    assert normalized is not None
    assert normalized.installs == 0


def test_tiktok_requires_descargas_and_kfc_tiktok_terms() -> None:
    valid = {
        "date": "2026-06-01",
        "account_id": "7127703579040743425",
        "campaign": "ECU_2026_KFC_TIKTOK_ONLINE_DESCARGAS_AON",
        "spend": "50",
        "app_install": "25",
    }
    missing_descargas = valid | {"campaign": "ECU_2026_KFC_TIKTOK_ONLINE_AON"}
    missing_kfc_tiktok = valid | {"campaign": "ECU_2026_TIKTOK_ONLINE_DESCARGAS_AON"}

    assert normalize_tiktok(valid) is not None
    assert normalize_tiktok(missing_descargas) is None
    assert normalize_tiktok(missing_kfc_tiktok) is None

