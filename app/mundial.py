from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional, Union


MUNDIAL_DASHBOARD_ID = "kfc-mundial"
MUNDIAL_TITLE = "Mundial Heavy Up · KFC App"
MUNDIAL_BRAND = "KFC"
MUNDIAL_SOURCE = "windsor"
MUNDIAL_START_DATE = date(2026, 6, 11)
MUNDIAL_EXTRA30_START = date(2026, 6, 30)
MUNDIAL_EXTRA30_END = date(2026, 7, 11)

META_APP_ACCOUNT_ID = "7266308733410766"
META_PYR_ACCOUNT_ID = "1170894797052218"
GOOGLE_ADS_ACCOUNTS = {
    ("DOM", "UAC"): "6975837337",
    ("DOM", "ACE"): "1087316000",
    ("EXP", "UAC"): "7526036272",
    ("EXP", "ACE"): "7526036272",
}

MUNDIAL_META_FIELDS = [
    "date",
    "account_id",
    "campaign",
    "adset_name",
    "spend",
    "actions_omni_purchase",
    "action_values_omni_purchase",
    "conversions_subscribe_total",
    "conversions_start_trial_total",
    "impressions",
    "clicks",
    "actions_mobile_app_install",
]
MUNDIAL_GOOGLE_ADS_FIELDS = [
    "date",
    "account_id",
    "campaign",
    "cost",
    "biddable_app_install_conversions",
]
MUNDIAL_GOOGLE_ADS_FALLBACK_FIELDS = [
    "date",
    "account_id",
    "campaign",
    "spend",
    "biddable_app_install_conversions",
]
MUNDIAL_GA4_FIELDS = [
    "date",
    "session_google_ads_campaign_name",
    "conversions_medios_purchase_delivery",
    "conversions_medios_purchase_express",
    "purchase_revenue",
]

HEAVY_UP_KEYS = ("ADQ|DOM", "ADQ|EXP", "RET|DOM", "RET|EXP")
GOOGLE_CHANNELS = ("DOM", "EXP")
GOOGLE_TYPES = ("UAC", "ACE")

MUNDIAL_MATCH_DAYS = [
    "2026-06-11",
    "2026-06-14",
    "2026-06-20",
    "2026-06-25",
    "2026-06-26",
    "2026-06-27",
    "2026-06-30",
    "2026-07-10",
    "2026-07-11",
]
MUNDIAL_ECU_DAYS = ["2026-06-14", "2026-06-20", "2026-06-25", "2026-06-30"]

MUNDIAL_VENTAS = {
    "2026-06-11": [75955, 45769, 30186],
    "2026-06-14": [165264, 117389, 47875],
    "2026-06-20": [131085, 88507, 42488],
    "2026-06-25": [117051, 73152, 43899],
    "2026-06-26": [91359, 57626, 33734],
    "2026-06-27": [92770, 58476, 33536],
}

# GA4 is the live source for Google purchases/revenue except for these client sheet dates.
GA4_SHEET_OVERRIDES = {
    ("2026-06-11", "DOM", "ACE"): ("703", "720", "19777.66"),
    ("2026-06-11", "DOM", "UAC"): ("120", "89", "2969.3"),
    ("2026-06-11", "EXP", "ACE"): ("309", "571", "11448.1"),
    ("2026-06-11", "EXP", "UAC"): ("99", "63", "2600.03"),
    ("2026-06-14", "DOM", "ACE"): ("1689", "1061", "46912.0"),
    ("2026-06-14", "DOM", "UAC"): ("297", "105", "7548.51"),
    ("2026-06-14", "EXP", "ACE"): ("615", "625", "19237.61"),
    ("2026-06-14", "EXP", "UAC"): ("256", "120", "6689.68"),
    ("2026-06-20", "DOM", "ACE"): ("1221", "951", "34752.59"),
    ("2026-06-20", "DOM", "UAC"): ("247", "99", "6269.35"),
    ("2026-06-20", "EXP", "ACE"): ("614", "691", "19253.03"),
    ("2026-06-20", "EXP", "UAC"): ("193", "102", "5081.52"),
    ("2026-06-25", "DOM", "ACE"): ("1029", "1016", "30435.53"),
    ("2026-06-25", "DOM", "UAC"): ("204", "126", "5479.3"),
    ("2026-06-25", "EXP", "ACE"): ("478", "699", "16282.19"),
    ("2026-06-25", "EXP", "UAC"): ("117", "87", "3086.92"),
    ("2026-06-26", "DOM", "ACE"): ("824", "814", "24065.32"),
    ("2026-06-26", "DOM", "UAC"): ("138", "102", "3575.0"),
    ("2026-06-26", "EXP", "ACE"): ("419", "591", "13607.75"),
    ("2026-06-26", "EXP", "UAC"): ("120", "87", "3188.04"),
    ("2026-06-27", "DOM", "ACE"): ("954", "806", "26040.85"),
    ("2026-06-27", "DOM", "UAC"): ("157", "75", "3553.15"),
    ("2026-06-27", "EXP", "ACE"): ("451", "553", "13666.3"),
    ("2026-06-27", "EXP", "UAC"): ("116", "83", "3153.4"),
    ("2026-06-30", "DOM", "ACE"): ("2116", "2020", "69625.17"),
    ("2026-06-30", "DOM", "UAC"): ("402", "298", "2473.56"),
    ("2026-06-30", "EXP", "ACE"): ("1064", "1421", "39235.09"),
    ("2026-06-30", "EXP", "UAC"): ("354", "284", "10938.94"),
}

_MONTH_LABELS = {6: "jun", 7: "jul"}
_ZERO = Decimal("0")
_TOKEN_RE = re.compile(r"[^A-Z0-9]+")


@dataclass(frozen=True)
class MundialRawRows:
    meta: list[dict[str, Any]]
    google_ads: list[dict[str, Any]]
    ga4: list[dict[str, Any]]


def build_mundial_payload(
    *,
    rows: MundialRawRows,
    from_date: date,
    to_date: date,
    updated_at: datetime,
    share_token: Optional[str] = None,
    public_token: Optional[str] = None,
    is_stale: bool = False,
    source_error: Optional[str] = None,
    source: str = MUNDIAL_SOURCE,
) -> dict[str, Any]:
    days = _date_range(from_date, to_date)
    days_iso = [day.isoformat() for day in days]
    meta = _aggregate_meta(rows.meta, days)
    google, google_days = _aggregate_google(rows.google_ads, rows.ga4, days)

    payload: dict[str, Any] = {
        "dashboardId": MUNDIAL_DASHBOARD_ID,
        "title": MUNDIAL_TITLE,
        "brand": MUNDIAL_BRAND,
        "isMock": False,
        "source": source,
        "updatedAt": _isoformat_z_ms(updated_at),
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "days": days_iso,
        "meta": meta,
        "google": google,
        "googleDays": google_days,
        "ventas": MUNDIAL_VENTAS,
        "matchDays": MUNDIAL_MATCH_DAYS,
        "ecuDays": MUNDIAL_ECU_DAYS,
        "matchDaysG": [_short_day(date.fromisoformat(day)) for day in MUNDIAL_MATCH_DAYS],
        "ecuDaysG": [_short_day(date.fromisoformat(day)) for day in MUNDIAL_ECU_DAYS],
        "rules": {
            "account": "L/C - Misiva - KFC - PERFORMANCE_INT FOOD_APP_",
            "period": f"{_short_day(from_date)} {from_date.year} → {_short_day(to_date)} {to_date.year}",
            "extractedAt": updated_at.astimezone(timezone.utc).date().isoformat(),
        },
        "shareToken": share_token,
        "publicToken": public_token,
    }
    if is_stale:
        payload["isStale"] = True
        payload["stale"] = True
    if source_error:
        payload["sourceError"] = source_error
    return payload


def sanitize_public_mundial_payload(payload: dict[str, Any], token: str) -> dict[str, Any]:
    allowed = {
        "dashboardId",
        "title",
        "brand",
        "isMock",
        "source",
        "updatedAt",
        "from",
        "to",
        "days",
        "meta",
        "google",
        "googleDays",
        "ventas",
        "matchDays",
        "ecuDays",
        "matchDaysG",
        "ecuDaysG",
        "rules",
        "publicToken",
        "isStale",
        "stale",
    }
    response = {key: value for key, value in payload.items() if key in allowed}
    response["publicToken"] = token
    return response


def _aggregate_meta(rows: list[dict[str, Any]], days: list[date]) -> dict[str, Any]:
    day_index = {day: idx for idx, day in enumerate(days)}
    heavy = {
        key: {metric: [_ZERO for _ in days] for metric in ("sp", "im", "cl", "p", "v")}
        for key in HEAVY_UP_KEYS
    }
    inst = {key: [_ZERO for _ in days] for key in HEAVY_UP_KEYS}
    events = {
        key: {"sub": [_ZERO for _ in days], "tri": [_ZERO for _ in days]}
        for key in HEAVY_UP_KEYS
    }
    aon = _empty_aon(days)
    aona = _empty_aona(days)
    extra30 = {
        "RET": {
            "E": {"sp": _ZERO, "p": _ZERO, "v": _ZERO, "tri": _ZERO, "sub": _ZERO},
            "D": {"sp": _ZERO, "p": _ZERO, "v": _ZERO, "sub": _ZERO, "tri": _ZERO},
        }
    }

    for row in rows:
        day = _safe_parse_date(_value(row, "date"))
        if day is None:
            continue
        account_id = _account_id(row)
        campaign = _string(row, "campaign")
        adset = _string(row, "adset_name", "adset")
        values = _meta_row_values(row)

        if day in day_index:
            heavy_key = _classify_heavy_up(campaign, adset, account_id)
            if heavy_key:
                idx = day_index[day]
                for metric in ("sp", "im", "cl", "p", "v"):
                    heavy[heavy_key][metric][idx] += values[metric]
                inst[heavy_key][idx] += values["inst"]
                events[heavy_key]["sub"][idx] += values["sub"]
                events[heavy_key]["tri"][idx] += values["tri"]

            aon_part = _classify_aon(campaign, adset, account_id)
            if aon_part:
                target = aon[day.isoformat()]
                _add_list(target["t"], [values["sp"], values["p"], values["v"]])
                if aon_part in ("e", "d"):
                    _add_list(
                        target[aon_part],
                        [values["sp"], values["p"], values["v"], values["sub"], values["tri"]],
                    )

            aona_part = _classify_aona(campaign, adset, account_id)
            if aona_part:
                _add_list(
                    aona[day.isoformat()][aona_part],
                    [values["sp"], values["p"], values["v"], values["sub"], values["tri"]],
                )

        extra_part = _classify_extra30(adset, account_id, day)
        if extra_part:
            bucket = extra30["RET"][extra_part]
            bucket["sp"] += values["sp"]
            bucket["p"] += values["p"]
            bucket["v"] += values["v"]
            bucket["sub"] += values["sub"]
            bucket["tri"] += values["tri"]

    extra_chart = {
        "RET|EXP": {
            "sp": _money(extra30["RET"]["E"]["sp"]),
            "p": _count(extra30["RET"]["E"]["p"]),
            "v": _money(extra30["RET"]["E"]["v"]),
        },
        "RET|DOM": {
            "sp": _money(extra30["RET"]["D"]["sp"]),
            "p": _count(extra30["RET"]["D"]["p"]),
            "v": _money(extra30["RET"]["D"]["v"]),
        },
    }
    return {
        "heavyUp": _finalize_heavy(heavy),
        "inst": {key: [_count(value) for value in series] for key, series in inst.items()},
        "events": _finalize_events(events),
        "extra30": _finalize_extra30(extra30),
        "extraChart": extra_chart,
        "aon": _finalize_aon(aon),
        "aona": _finalize_aona(aona),
    }


def _aggregate_google(
    google_ads_rows: list[dict[str, Any]],
    ga4_rows: list[dict[str, Any]],
    days: list[date],
) -> tuple[dict[str, list[list[Any]]], list[str]]:
    day_set = set(days)
    ads: dict[tuple[date, str, str], dict[str, Decimal]] = {}
    ga4: dict[tuple[date, str, str], dict[str, Decimal]] = {}

    for row in google_ads_rows:
        day = _safe_parse_date(_value(row, "date"))
        if day not in day_set:
            continue
        campaign = _string(row, "campaign")
        classified = _classify_google_campaign(campaign)
        if not classified:
            continue
        channel, typ = classified
        account_id = _normalized_account_id(_account_id(row))
        expected_account = GOOGLE_ADS_ACCOUNTS[(channel, typ)]
        if account_id and account_id != expected_account:
            continue
        key = (day, channel, typ)
        bucket = ads.setdefault(key, {"inv": _ZERO, "inst": _ZERO})
        bucket["inv"] += _decimal(row, "cost", "spend")
        if typ == "UAC":
            bucket["inst"] += _decimal(row, "biddable_app_install_conversions")

    for row in ga4_rows:
        day = _safe_parse_date(_value(row, "date"))
        if day not in day_set:
            continue
        campaign = _string(row, "session_google_ads_campaign_name")
        campaign_tokens = _tokens(campaign)
        if not {"ECU", "2026", "JULIO", "ONLINE"}.issubset(campaign_tokens):
            continue
        classified = _classify_google_campaign(campaign)
        if not classified:
            continue
        key = (day, classified[0], classified[1])
        bucket = ga4.setdefault(key, {"deliv": _ZERO, "express": _ZERO, "revenue": _ZERO})
        bucket["deliv"] += _decimal(row, "conversions_medios_purchase_delivery")
        bucket["express"] += _decimal(row, "conversions_medios_purchase_express")
        bucket["revenue"] += _decimal(row, "purchase_revenue")

    for (day_iso, channel, typ), values in GA4_SHEET_OVERRIDES.items():
        day = date.fromisoformat(day_iso)
        if day not in day_set:
            continue
        ga4[(day, channel, typ)] = {
            "deliv": Decimal(values[0]),
            "express": Decimal(values[1]),
            "revenue": Decimal(values[2]),
        }

    google_days = [
        day
        for day in days
        if any(
            _has_google_activity(ads, ga4, day, channel, typ)
            for channel in GOOGLE_CHANNELS
            for typ in GOOGLE_TYPES
        )
    ]
    output = {"DOM": [], "EXP": []}
    for channel in GOOGLE_CHANNELS:
        for day in google_days:
            for typ in GOOGLE_TYPES:
                output[channel].append(_google_row(day, channel, typ, ads, ga4))
    return output, [_short_day(day) for day in google_days]


def _google_row(
    day: date,
    channel: str,
    typ: str,
    ads: dict[tuple[date, str, str], dict[str, Decimal]],
    ga4: dict[tuple[date, str, str], dict[str, Decimal]],
) -> list[Any]:
    key = (day, channel, typ)
    ad_values = ads.get(key, {"inv": _ZERO, "inst": _ZERO})
    ga4_values = ga4.get(key, {"deliv": _ZERO, "express": _ZERO, "revenue": _ZERO})
    inv = ad_values["inv"]
    installs = ad_values["inst"]
    purchases_deliv = ga4_values["deliv"]
    purchases_exp = ga4_values["express"]
    purchases_total = purchases_deliv + purchases_exp
    revenue = ga4_values["revenue"]
    revenue_share = purchases_deliv / purchases_total if purchases_total else _ZERO
    value_conj = revenue * revenue_share

    return [
        _short_day(day),
        typ,
        _count(purchases_total),
        _count(purchases_deliv),
        _count(purchases_exp),
        _ratio(inv, purchases_deliv, zero=Decimal("0")),
        _money(revenue),
        _money(value_conj),
        _ratio(value_conj, inv, zero=Decimal("0")),
        _money(inv),
        _ratio(revenue, inv, zero=Decimal("0")),
        _count(installs) if typ == "UAC" else None,
        _ratio(inv, installs) if typ == "UAC" else None,
    ]


def _has_google_activity(
    ads: dict[tuple[date, str, str], dict[str, Decimal]],
    ga4: dict[tuple[date, str, str], dict[str, Decimal]],
    day: date,
    channel: str,
    typ: str,
) -> bool:
    key = (day, channel, typ)
    ad_values = ads.get(key)
    ga4_values = ga4.get(key)
    if ad_values and (ad_values["inv"] or ad_values["inst"]):
        return True
    if ga4_values and (ga4_values["deliv"] or ga4_values["express"] or ga4_values["revenue"]):
        return True
    return False


def _classify_heavy_up(campaign: str, adset: str, account_id: str) -> Optional[str]:
    if account_id and account_id != META_APP_ACCOUNT_ID:
        return None
    campaign_tokens = _tokens(campaign)
    combined_tokens = _tokens(f"{campaign} {adset}")
    if not {"HEAVY", "UP", "MUNDIAL", "APP"}.issubset(campaign_tokens):
        return None
    if {"DIA", "DEL", "POLLO"}.issubset(combined_tokens):
        return None
    if "CUARTOS" not in combined_tokens:
        return None
    channel = _meta_channel(combined_tokens)
    if not channel:
        return None
    campaign_type = _meta_campaign_type(combined_tokens)
    if not campaign_type:
        return None
    return f"{campaign_type}|{channel}"


def _classify_aon(campaign: str, adset: str, account_id: str) -> Optional[str]:
    if account_id and account_id != META_APP_ACCOUNT_ID:
        return None
    campaign_tokens = _tokens(campaign)
    if not {"RETENCION", "AON"}.issubset(campaign_tokens):
        return None
    adset_tokens = _tokens(adset)
    if "EXPRESS" in adset_tokens:
        return "e"
    if "DOMICILIO" in adset_tokens:
        return "d"
    return "t"


def _classify_aona(campaign: str, adset: str, account_id: str) -> Optional[str]:
    if account_id and account_id != META_APP_ACCOUNT_ID:
        return None
    campaign_tokens = _tokens(campaign)
    adset_tokens = _tokens(adset)
    if "PARAGUAS" not in campaign_tokens:
        return None
    if not {"MUNDIAL", "ADQUISICION"}.issubset(adset_tokens):
        return None
    if "ESPACIO" in adset_tokens or "ESPACIO" in campaign_tokens:
        return "a"
    return "m"


def _classify_extra30(adset: str, account_id: str, day: date) -> Optional[str]:
    if day < MUNDIAL_EXTRA30_START or day > MUNDIAL_EXTRA30_END:
        return None
    tokens = _tokens(adset)
    if account_id == META_APP_ACCOUNT_ID and {"SEGUNDA", "ACTIVACION"}.issubset(tokens):
        return "D"
    if account_id == META_PYR_ACCOUNT_ID and {"40", "OFF", "30", "JUNIO"}.issubset(tokens):
        return "E"
    return None


def _classify_google_campaign(campaign: str) -> Optional[tuple[str, str]]:
    tokens = _tokens(campaign)
    normalized = _normalized_text(campaign)
    if "PARAGUAS" in tokens:
        return None
    if "UAC" in tokens:
        typ = "UAC"
    elif "ACE" in tokens:
        typ = "ACE"
    else:
        return None
    if typ == "UAC" and "ADQUISICION" not in tokens:
        return None
    if typ == "ACE" and "RETENCION" not in tokens:
        return None
    if "DOMICILIO APP" in normalized:
        return ("DOM", typ)
    if "EXPRESS" in tokens:
        return ("EXP", typ)
    return None


def _meta_channel(tokens: set[str]) -> Optional[str]:
    if "DOMICILIO" in tokens:
        return "DOM"
    if "EXPRESS" in tokens:
        return "EXP"
    return None


def _meta_campaign_type(tokens: set[str]) -> Optional[str]:
    if "RETENCION" in tokens or "RET" in tokens:
        return "RET"
    if "ADQUISICION" in tokens or "ADQ" in tokens:
        return "ADQ"
    return None


def _meta_row_values(row: dict[str, Any]) -> dict[str, Decimal]:
    return {
        "sp": _decimal(row, "spend"),
        "im": _decimal(row, "impressions"),
        "cl": _decimal(row, "clicks"),
        "p": _decimal(row, "actions_omni_purchase"),
        "v": _decimal(row, "action_values_omni_purchase"),
        "sub": _decimal(row, "conversions_subscribe_total"),
        "tri": _decimal(row, "conversions_start_trial_total"),
        "inst": _decimal(row, "actions_mobile_app_install"),
    }


def _empty_aon(days: list[date]) -> dict[str, dict[str, list[Decimal]]]:
    return {
        day.isoformat(): {
            "t": [_ZERO, _ZERO, _ZERO],
            "e": [_ZERO, _ZERO, _ZERO, _ZERO, _ZERO],
            "d": [_ZERO, _ZERO, _ZERO, _ZERO, _ZERO],
        }
        for day in days
    }


def _empty_aona(days: list[date]) -> dict[str, dict[str, list[Decimal]]]:
    return {
        day.isoformat(): {
            "m": [_ZERO, _ZERO, _ZERO, _ZERO, _ZERO],
            "a": [_ZERO, _ZERO, _ZERO, _ZERO, _ZERO],
        }
        for day in days
    }


def _finalize_heavy(heavy: dict[str, dict[str, list[Decimal]]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, metrics in heavy.items():
        output[key] = {
            "sp": [_money(value) for value in metrics["sp"]],
            "im": [_count(value) for value in metrics["im"]],
            "cl": [_count(value) for value in metrics["cl"]],
            "p": [_count(value) for value in metrics["p"]],
            "v": [_money(value) for value in metrics["v"]],
        }
    return output


def _finalize_events(events: dict[str, dict[str, list[Decimal]]]) -> dict[str, Any]:
    return {
        key: {
            "sub": [_count(value) for value in metrics["sub"]],
            "tri": [_count(value) for value in metrics["tri"]],
        }
        for key, metrics in events.items()
    }


def _finalize_extra30(extra30: dict[str, Any]) -> dict[str, Any]:
    ret = extra30["RET"]
    return {
        "RET": {
            "E": {
                "sp": _money(ret["E"]["sp"]),
                "p": _count(ret["E"]["p"]),
                "v": _money(ret["E"]["v"]),
                "tri": _count(ret["E"]["tri"]),
                "sub": _count(ret["E"]["sub"]),
            },
            "D": {
                "sp": _money(ret["D"]["sp"]),
                "p": _count(ret["D"]["p"]),
                "v": _money(ret["D"]["v"]),
                "sub": _count(ret["D"]["sub"]),
                "tri": _count(ret["D"]["tri"]),
            },
        }
    }


def _finalize_aon(aon: dict[str, dict[str, list[Decimal]]]) -> dict[str, Any]:
    return {
        day: {
            "t": [_money(values["t"][0]), _count(values["t"][1]), _money(values["t"][2])],
            "e": [
                _money(values["e"][0]),
                _count(values["e"][1]),
                _money(values["e"][2]),
                _count(values["e"][3]),
                _count(values["e"][4]),
            ],
            "d": [
                _money(values["d"][0]),
                _count(values["d"][1]),
                _money(values["d"][2]),
                _count(values["d"][3]),
                _count(values["d"][4]),
            ],
        }
        for day, values in aon.items()
    }


def _finalize_aona(aona: dict[str, dict[str, list[Decimal]]]) -> dict[str, Any]:
    return {
        day: {
            "m": [
                _money(values["m"][0]),
                _count(values["m"][1]),
                _money(values["m"][2]),
                _count(values["m"][3]),
                _count(values["m"][4]),
            ],
            "a": [
                _money(values["a"][0]),
                _count(values["a"][1]),
                _money(values["a"][2]),
                _count(values["a"][3]),
                _count(values["a"][4]),
            ],
        }
        for day, values in aona.items()
    }


def _add_list(target: list[Decimal], values: list[Decimal]) -> None:
    for idx, value in enumerate(values):
        target[idx] += value


def _date_range(start: date, end: date) -> list[date]:
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _short_day(day: date) -> str:
    return f"{day.day:02d} {_MONTH_LABELS.get(day.month, day.strftime('%b').lower())}"


def _isoformat_z_ms(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ratio(
    numerator: Decimal,
    denominator: Decimal,
    *,
    zero: Optional[Decimal] = None,
) -> Optional[float]:
    if denominator == 0:
        if zero is None:
            return None
        return _money(zero)
    return _money(numerator / denominator)


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _count(value: Decimal) -> Union[int, float]:
    integral = value.to_integral_value(rounding=ROUND_HALF_UP)
    if value == integral:
        return int(integral)
    return float(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def _decimal(row: dict[str, Any], *keys: str) -> Decimal:
    value = _value(row, *keys)
    if value is None or value == "":
        return _ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    text = str(value).strip().replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def _safe_parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _string(row: dict[str, Any], *keys: str) -> str:
    value = _value(row, *keys)
    return "" if value is None else str(value).strip()


def _account_id(row: dict[str, Any]) -> str:
    return _string(
        row,
        "account_id",
        "account",
        "accountid",
        "customer_id",
        "customer",
        "customer.id",
    )


def _normalized_account_id(account_id: str) -> str:
    return account_id.replace("-", "").replace(" ", "").strip()


def _tokens(value: str) -> set[str]:
    return set(_normalized_text(value).split())


def _normalized_text(value: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return _TOKEN_RE.sub(" ", ascii_text.upper()).strip()
