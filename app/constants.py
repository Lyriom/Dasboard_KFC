from __future__ import annotations

from datetime import date

DASHBOARD_ID = "kfc-app-installs"
DASHBOARD_TITLE = "KFC Instalaciones App"
BRAND = "KFC"
SOURCE = "windsor"
BASE_START_DATE = date(2025, 12, 29)

PLATFORMS = ("meta", "tiktok", "google")

META_ACCOUNT_IDS = {
    "7266308733410766",
    "652936112244737",
    "7650587078296233",
    "1170894797052218",
    "447831050510903",
    "705688263919959",
}
META_FIELDS = [
    "date",
    "account_id",
    "campaign",
    "campaign_objective",
    "spend",
    "actions_mobile_app_install",
]
META_CAMPAIGN_OBJECTIVE = "OUTCOME_APP_PROMOTION"

TIKTOK_ACCOUNT_IDS = {
    "7127703579040743425",
    "7114431556009066498",
}
TIKTOK_FIELDS = [
    "date",
    "account_id",
    "campaign",
    "spend",
    "app_install",
]
TIKTOK_REQUIRED_CAMPAIGN_TERMS = ("DESCARGAS", "KFC_TIKTOK")

GOOGLE_ACCOUNT_IDS = {
    "697-583-7337": "KFC_PERFORMANCE_APP",
    "372-580-6060": "KFC_PERFORMANCE_OFFLINE",
    "752-603-6272": "KFC_PERFORMANCE_APPEX",
}
GOOGLE_ACCOUNT_IDS_NORMALIZED = {
    account_id.replace("-", "") for account_id in GOOGLE_ACCOUNT_IDS
}
GOOGLE_FIELDS = [
    "date",
    "account_id",
    "campaign",
    "spend",
    "biddable_app_install_conversions",
]
GOOGLE_CAMPAIGN_EXACT = (
    "ECU_2026_JUNIO_INT FOOD SERVICES CORP "
    "SA_KFC_GOOGLE_OFFLINE_CUPONES_UAC_CONSIDERACION_DESCARGAS_AON_N/A_ADQUISICION_N/A_"
)
GOOGLE_INSTALL_FIELD = "biddable_app_install_conversions"

