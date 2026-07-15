from __future__ import annotations

from datetime import date, datetime, timezone

from app.mundial import MundialRawRows, build_mundial_payload


def test_mundial_payload_aggregates_meta_and_google_contract() -> None:
    payload = build_mundial_payload(
        rows=MundialRawRows(
            meta=[
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_KFC_META_HEAVY UP_MUNDIAL APP_ADQUISICION",
                    "adset_name": "ADQUISICION DOMICILIO CUARTOS",
                    "spend": "10.10",
                    "actions_omni_purchase": "2",
                    "action_values_omni_purchase": "30.30",
                    "conversions_subscribe_total": "1",
                    "conversions_start_trial_total": "3",
                    "impressions": "100",
                    "clicks": "9",
                    "actions_mobile_app_install": "4",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_KFC_META_HEAVY UP_MUNDIAL APP_ADQUISICION",
                    "adset_name": "JUNIO_KFC_META_MOBILE/DESKTOP_OPEN PROSPECTING_APP_DOMICILIO_ADQUISICION_",
                    "spend": "20",
                    "actions_omni_purchase": "3",
                    "action_values_omni_purchase": "40",
                    "conversions_subscribe_total": "2",
                    "conversions_start_trial_total": "4",
                    "impressions": "200",
                    "clicks": "19",
                    "actions_mobile_app_install": "5",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_KFC_META_HEAVY UP_MUNDIAL APP_ADQUISICION",
                    "adset_name": "ADQUISICION DOMICILIO DIA DEL POLLO CUARTOS",
                    "spend": "999",
                    "actions_omni_purchase": "999",
                    "action_values_omni_purchase": "999",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_MUNDIAL APP_RETENCION AON_RETENCION_N/A_",
                    "adset_name": "EXPRESS",
                    "spend": "15.61",
                    "actions_omni_purchase": "25",
                    "action_values_omni_purchase": "367.12",
                    "conversions_subscribe_total": "12",
                    "conversions_start_trial_total": "13",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_MUNDIAL APP_RETENCION AON_RETENCION_N/A_",
                    "adset_name": "DOMICILIO",
                    "spend": "67.02",
                    "actions_omni_purchase": "162",
                    "action_values_omni_purchase": "2165.52",
                    "conversions_subscribe_total": "70",
                    "conversions_start_trial_total": "84",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_MUNDIAL APP_RETENCION AON_RETENCION_N/A_",
                    "adset_name": "AON+PROMOS",
                    "spend": "5",
                    "actions_omni_purchase": "6",
                    "action_values_omni_purchase": "7",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_PARAGUAS_AON REACTIVAR_ACCIONES DE VALOR_PURCHASE_AON_APP_RETENCION_N/A_",
                    "adset_name": "AON REACTIVAR",
                    "spend": "999",
                    "actions_omni_purchase": "999",
                    "action_values_omni_purchase": "999",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_PARAGUAS_AON DIPPING MUNDIAL_ADQUISICION",
                    "adset_name": "MAYO_MUNDIAL_ADQUISICION_",
                    "spend": "104.57",
                    "actions_omni_purchase": "38",
                    "action_values_omni_purchase": "597.58",
                    "conversions_subscribe_total": "19",
                    "conversions_start_trial_total": "21",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_PARAGUAS_AUDIENCIA ESPACIO DIPPING_LOW END_MUNDIAL_ADQUISICION",
                    "adset_name": "AU ESPACIO MUNDIAL_MUNDIAL_ADQUISICION",
                    "spend": "32.25",
                    "actions_omni_purchase": "41",
                    "action_values_omni_purchase": "533.18",
                    "conversions_subscribe_total": "18",
                    "conversions_start_trial_total": "23",
                },
                {
                    "date": "2026-06-11",
                    "account_id": "7266308733410766",
                    "campaign": "ECU_2026_JULIO_PARAGUAS_DESCARGAS ADVANTAGE_ADQUISICION",
                    "adset_name": "DESCARGAS MUNDIAL ESPACIO ADVANTAGE_ADQUISICION",
                    "spend": "999",
                    "actions_omni_purchase": "999",
                    "action_values_omni_purchase": "999",
                },
                {
                    "date": "2026-06-30",
                    "account_id": "7266308733410766",
                    "adset_name": "SEGUNDA ACTIVACION",
                    "spend": "513.03",
                    "actions_omni_purchase": "1009",
                    "action_values_omni_purchase": "16883.99",
                    "conversions_subscribe_total": "565",
                    "conversions_start_trial_total": "407",
                },
                {
                    "date": "2026-07-01",
                    "account_id": "1170894797052218",
                    "adset_name": "40 OFF 30 JUNIO",
                    "spend": "463.31",
                    "actions_omni_purchase": "1379",
                    "action_values_omni_purchase": "22559.83",
                    "conversions_subscribe_total": "618",
                    "conversions_start_trial_total": "751",
                },
            ],
            google_ads=[
                google_row("108-731-6000", "DOMICILIO APP_UAC_ADQUISICION_N/A_", "388.14", "756"),
                google_row(
                    "697-583-7337",
                    "DOMICILIO APP_ACE RETENCION DESARROLLAR_RETENCION_N/A_",
                    "444.42",
                    "999",
                ),
                google_row("752-603-6272", "EXPRESS_UAC_ADQUISICION_N/A_", "180.34", "752"),
                google_row("752-603-6272", "EXPRESS_ACE_RETENCION_N/A_", "364.03", "999"),
            ],
            ga4=[
                ga4_row("DOMICILIO APP_UAC_ADQUISICION_N/A_", "1", "1", "1"),
                ga4_row(
                    "DOMICILIO APP_UAC_ADQUISICION_N/A_",
                    "999",
                    "999",
                    "999",
                    account_id="519268254",
                ),
                ga4_row("DOMICILIO APP_ACE RETENCION DESARROLLAR_RETENCION_N/A_", "1", "1", "1"),
                ga4_row("EXPRESS_UAC_ADQUISICION_N/A_", "1", "1", "1"),
                ga4_row("EXPRESS_ACE_RETENCION_N/A_", "1", "1", "1"),
            ],
        ),
        from_date=date(2026, 6, 11),
        to_date=date(2026, 6, 11),
        updated_at=datetime(2026, 7, 13, 22, tzinfo=timezone.utc),
    )

    assert payload["dashboardId"] == "kfc-mundial"
    assert payload["isMock"] is False
    assert payload["source"] == "windsor"
    assert payload["days"] == ["2026-06-11"]
    assert payload["meta"]["heavyUp"]["ADQ|DOM"]["sp"] == [30.1]
    assert payload["meta"]["heavyUp"]["ADQ|DOM"]["p"] == [5]
    assert payload["meta"]["inst"]["ADQ|DOM"] == [9]
    assert payload["meta"]["events"]["ADQ|DOM"] == {"sub": [3], "tri": [7]}
    assert payload["meta"]["aon"]["2026-06-11"]["t"] == [87.63, 193, 2539.64]
    assert payload["meta"]["aon"]["2026-06-11"]["e"] == [15.61, 25, 367.12, 12, 13]
    assert payload["meta"]["aona"]["2026-06-11"]["m"] == [104.57, 38, 597.58, 19, 21]
    assert payload["meta"]["aona"]["2026-06-11"]["a"] == [32.25, 41, 533.18, 18, 23]
    assert payload["meta"]["extra30"]["RET"]["E"] == {
        "sp": 463.31,
        "p": 1379,
        "v": 22559.83,
        "tri": 751,
        "sub": 618,
    }
    assert payload["meta"]["extraChart"]["RET|DOM"] == {"sp": 513.03, "p": 1009, "v": 16883.99}
    assert payload["google"]["DOM"][0] == [
        "11 jun",
        "UAC",
        209,
        120,
        89,
        3.23,
        2969.3,
        1704.86,
        4.39,
        388.14,
        7.65,
        756,
        0.51,
    ]
    assert payload["google"]["DOM"][1][11] is None
    assert payload["google"]["DOM"][1][12] is None
    assert payload["google"]["EXP"][0][:11] == [
        "11 jun",
        "UAC",
        162,
        99,
        63,
        1.82,
        2600.03,
        1588.91,
        8.81,
        180.34,
        14.42,
    ]


def test_google_non_override_day_uses_ga4_and_biddable_installs() -> None:
    payload = build_mundial_payload(
        rows=MundialRawRows(
            meta=[],
            google_ads=[
                google_row(
                    "108-731-6000",
                    "DOMICILIO APP_UAC_ADQUISICION_N/A_",
                    "100",
                    "20",
                    "2026-07-01",
                )
            ],
            ga4=[ga4_row("DOMICILIO APP_UAC_ADQUISICION_N/A_", "25", "75", "1000", "2026-07-01")],
        ),
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 1),
        updated_at=datetime(2026, 7, 13, 22, tzinfo=timezone.utc),
    )

    assert payload["googleDays"] == ["01 jul"]
    assert payload["google"]["DOM"][0] == [
        "01 jul",
        "UAC",
        100,
        25,
        75,
        4.0,
        1000.0,
        250.0,
        2.5,
        100.0,
        10.0,
        20,
        5.0,
    ]


def google_row(
    account_id: str,
    campaign_tail: str,
    cost: str,
    installs: str,
    day: str = "2026-06-11",
) -> dict:
    return {
        "date": day,
        "account_id": account_id,
        "campaign": f"ECU_2026_JULIO_KFC_GOOGLE_ONLINE_{campaign_tail}",
        "cost": cost,
        "biddable_app_install_conversions": installs,
        "conversions": "999999",
    }


def ga4_row(
    campaign_tail: str,
    delivery: str,
    express: str,
    revenue: str,
    day: str = "2026-06-11",
    account_id: str = "204861780",
) -> dict:
    return {
        "date": day,
        "account_id": account_id,
        "session_google_ads_campaign_name": f"ECU_2026_JULIO_KFC_GOOGLE_ONLINE_{campaign_tail}",
        "conversions_medios_purchase_delivery": delivery,
        "conversions_medios_purchase_express": express,
        "purchase_revenue": revenue,
    }
