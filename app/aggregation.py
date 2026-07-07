from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Literal, Optional, Union

from app.constants import (
    BASE_START_DATE,
    BRAND,
    DASHBOARD_ID,
    DASHBOARD_TITLE,
    GOOGLE_ACCOUNT_IDS_NORMALIZED,
    GOOGLE_CAMPAIGN_EXACT,
    GOOGLE_INSTALL_FIELD,
    META_ACCOUNT_IDS,
    META_CAMPAIGN_OBJECTIVE,
    PLATFORMS,
    SOURCE,
    TIKTOK_ACCOUNT_IDS,
    TIKTOK_REQUIRED_CAMPAIGN_TERMS,
)

Platform = Literal["meta", "tiktok", "google"]


@dataclass(frozen=True)
class NormalizedDaily:
    date: date
    platform: Platform
    account_id: str
    campaign: str
    spend: Decimal
    installs: Decimal
    raw_hash: str


def normalize_meta(row: dict[str, Any]) -> Optional[NormalizedDaily]:
    account_id = _string_value(row, "account_id")
    if account_id not in META_ACCOUNT_IDS:
        return None
    objective = _string_value(row, "campaign_objective")
    if objective != META_CAMPAIGN_OBJECTIVE:
        return None
    return NormalizedDaily(
        date=parse_date(_row_value(row, "date")),
        platform="meta",
        account_id=account_id,
        campaign=_string_value(row, "campaign"),
        spend=to_decimal(_row_value(row, "spend")),
        installs=to_decimal(_row_value(row, "actions_mobile_app_install")),
        raw_hash=raw_hash(row),
    )


def normalize_tiktok(row: dict[str, Any]) -> Optional[NormalizedDaily]:
    account_id = _string_value(row, "account_id")
    if account_id not in TIKTOK_ACCOUNT_IDS:
        return None
    campaign = _string_value(row, "campaign")
    campaign_upper = campaign.upper()
    if not all(term in campaign_upper for term in TIKTOK_REQUIRED_CAMPAIGN_TERMS):
        return None
    return NormalizedDaily(
        date=parse_date(_row_value(row, "date")),
        platform="tiktok",
        account_id=account_id,
        campaign=campaign,
        spend=to_decimal(_row_value(row, "spend")),
        installs=to_decimal(_row_value(row, "app_install")),
        raw_hash=raw_hash(row),
    )


def normalize_google(row: dict[str, Any]) -> Optional[NormalizedDaily]:
    account_id = _string_value(
        row,
        "account_id",
        "customer_id",
        "customer",
        "customer.id",
        "customer_account_id",
    )
    if _normalize_account_id(account_id) not in GOOGLE_ACCOUNT_IDS_NORMALIZED:
        return None
    campaign = _string_value(row, "campaign")
    if campaign != GOOGLE_CAMPAIGN_EXACT:
        return None
    return NormalizedDaily(
        date=parse_date(_row_value(row, "date")),
        platform="google",
        account_id=account_id,
        campaign=campaign,
        spend=to_decimal(_row_value(row, "spend")),
        installs=to_decimal(_row_value(row, GOOGLE_INSTALL_FIELD)),
        raw_hash=raw_hash(row),
    )


def normalize_rows(platform: Platform, rows: list[dict[str, Any]]) -> list[NormalizedDaily]:
    normalizer = {
        "meta": normalize_meta,
        "tiktok": normalize_tiktok,
        "google": normalize_google,
    }[platform]
    normalized: list[NormalizedDaily] = []
    for row in rows:
        item = normalizer(row)
        if item is not None:
            normalized.append(item)
    return normalized


def aggregate_weekly(
    rows: list[Any],
    from_date: date,
    to_date: date,
) -> list[dict[str, Any]]:
    if to_date < from_date:
        return []

    start = week_start_for(max(from_date, BASE_START_DATE))
    buckets: dict[date, dict[str, Any]] = {}
    cursor = start
    while cursor <= to_date:
        buckets[cursor] = {
            platform: {"spend": Decimal("0"), "installs": Decimal("0")}
            for platform in PLATFORMS
        }
        cursor += timedelta(days=7)

    for row in rows:
        row_date = _attr(row, "date")
        if isinstance(row_date, datetime):
            row_date = row_date.date()
        if row_date < from_date or row_date > to_date or row_date < BASE_START_DATE:
            continue
        platform = str(_attr(row, "platform")).lower()
        if platform not in PLATFORMS:
            continue
        week_start = week_start_for(row_date)
        if week_start not in buckets:
            continue
        buckets[week_start][platform]["spend"] += to_decimal(_attr(row, "spend"))
        buckets[week_start][platform]["installs"] += to_decimal(_attr(row, "installs"))

    weeks: list[dict[str, Any]] = []
    for week_start, platform_totals in buckets.items():
        week_end = week_start + timedelta(days=6)
        response_week: dict[str, Any] = {
            "weekNumber": ((week_start - BASE_START_DATE).days // 7) + 1,
            "weekStart": week_start.isoformat(),
            "weekEnd": week_end.isoformat(),
            "weekLabel": f"{week_start:%d/%m}-{week_end:%d/%m}",
        }

        total_spend = Decimal("0")
        total_installs = Decimal("0")
        for platform in PLATFORMS:
            spend = platform_totals[platform]["spend"]
            installs = platform_totals[platform]["installs"]
            total_spend += spend
            total_installs += installs
            response_week[platform] = _metric_response(spend, installs)

        response_week["total"] = _metric_response(total_spend, total_installs)
        weeks.append(response_week)

    return weeks


def build_dashboard_payload(
    *,
    weeks: list[dict[str, Any]],
    from_date: date,
    to_date: date,
    updated_at: datetime,
    share_token: Optional[str] = None,
    is_mock: bool = False,
    is_stale: bool = False,
    source_error: Optional[str] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dashboardId": DASHBOARD_ID,
        "title": DASHBOARD_TITLE,
        "brand": BRAND,
        "isMock": is_mock,
        "source": SOURCE,
        "updatedAt": isoformat_z(updated_at),
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "shareToken": share_token,
        "weeks": weeks,
    }
    if is_stale:
        payload["isStale"] = True
    if source_error:
        payload["sourceError"] = source_error
    return payload


def sanitize_public_dashboard(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "dashboardId",
        "title",
        "brand",
        "source",
        "updatedAt",
        "from",
        "to",
        "weeks",
        "isStale",
    }
    return {key: value for key, value in payload.items() if key in allowed}


def week_start_for(day: date) -> date:
    if day < BASE_START_DATE:
        return BASE_START_DATE
    offset = (day - BASE_START_DATE).days
    return BASE_START_DATE + timedelta(days=(offset // 7) * 7)


def parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if value is None:
        raise ValueError("date is required")
    text = str(value).strip()
    if not text:
        raise ValueError("date is required")
    return date.fromisoformat(text[:10])


def to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    text = str(value).strip().replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def raw_hash(row: dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def isoformat_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _metric_response(spend: Decimal, installs: Decimal) -> dict[str, Any]:
    return {
        "spend": _money(spend),
        "installs": _count(installs),
        "cpd": _cpd(spend, installs),
    }


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _count(value: Decimal) -> Union[int, float]:
    integral = value.to_integral_value(rounding=ROUND_HALF_UP)
    if value == integral:
        return int(integral)
    return float(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def _cpd(spend: Decimal, installs: Decimal) -> Optional[float]:
    if installs == 0:
        return None
    return float((spend / installs).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def _row_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _string_value(row: dict[str, Any], *keys: str) -> str:
    value = _row_value(row, *keys)
    return "" if value is None else str(value).strip()


def _normalize_account_id(account_id: str) -> str:
    return account_id.replace("-", "").replace(" ", "")


def _attr(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row[name]
    return getattr(row, name)
