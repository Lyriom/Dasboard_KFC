from __future__ import annotations

import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import KfcMundialShare, KfcMundialSnapshot, utcnow
from app.mundial import (
    MUNDIAL_EXTRA30_END,
    MUNDIAL_GA4_FIELDS,
    MUNDIAL_GOOGLE_ADS_FALLBACK_FIELDS,
    MUNDIAL_GOOGLE_ADS_FIELDS,
    MUNDIAL_META_FIELDS,
    MUNDIAL_START_DATE,
    MundialRawRows,
    build_mundial_payload,
    sanitize_public_mundial_payload,
)
from app.security import AuthUser
from app.windsor import WindsorClient, WindsorError


logger = logging.getLogger(__name__)


class MundialDashboardUnavailable(RuntimeError):
    pass


def today_in_mundial_timezone(settings: Settings) -> date:
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def normalize_mundial_range(
    from_date: Optional[date],
    to_date: Optional[date],
    settings: Settings,
) -> tuple[date, date]:
    start = from_date or MUNDIAL_START_DATE
    end = to_date or today_in_mundial_timezone(settings)
    if start < MUNDIAL_START_DATE:
        start = MUNDIAL_START_DATE
    if end < start:
        raise ValueError("to must be greater than or equal to from")
    return start, end


def get_mundial_dashboard(
    db: Session,
    settings: Settings,
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    force_refresh: bool = False,
    public_token: Optional[str] = None,
) -> dict:
    start, end = normalize_mundial_range(from_date, to_date, settings)
    snapshot = latest_mundial_snapshot(db, start, end)

    if snapshot and not force_refresh and _is_fresh(snapshot, settings):
        return _prepare_mundial_payload(db, dict(snapshot.payload_json), public_token=public_token)

    try:
        payload = refresh_mundial_dashboard(db, settings, from_date=start, to_date=end)
        return _prepare_mundial_payload(db, payload, public_token=public_token)
    except WindsorError as exc:
        if snapshot:
            payload = dict(snapshot.payload_json)
            payload["isStale"] = True
            payload["stale"] = True
            payload["source"] = "snapshot"
            payload["sourceError"] = "windsor_unavailable"
            return _prepare_mundial_payload(db, payload, public_token=public_token)
        raise MundialDashboardUnavailable("No cached mundial dashboard is available") from exc


def refresh_mundial_dashboard(
    db: Session,
    settings: Settings,
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> dict:
    start, end = normalize_mundial_range(from_date, to_date, settings)
    client = WindsorClient(settings)
    fetch_end = max(end, MUNDIAL_EXTRA30_END)

    errors: list[str] = []
    successful_connectors = 0

    try:
        raw_meta = _fetch_connector_or_raise(
            client,
            "facebook",
            MUNDIAL_META_FIELDS,
            MUNDIAL_START_DATE,
            fetch_end,
        )
        successful_connectors += 1
    except WindsorError as exc:
        raw_meta = []
        errors.append(str(exc))

    try:
        raw_google = _fetch_google_ads(client, start, end)
        successful_connectors += 1
    except WindsorError as exc:
        raw_google = []
        errors.append(str(exc))

    try:
        raw_ga4 = _fetch_connector_or_raise(
            client,
            "googleanalytics4",
            MUNDIAL_GA4_FIELDS,
            start,
            end,
        )
        successful_connectors += 1
    except WindsorError as exc:
        raw_ga4 = []
        errors.append(str(exc))

    if successful_connectors == 0:
        raise WindsorError("All Mundial Windsor connectors failed: " + "; ".join(errors))

    source_updated_at = utcnow()
    share = get_active_mundial_share(db)
    payload = build_mundial_payload(
        rows=MundialRawRows(meta=raw_meta, google_ads=raw_google, ga4=raw_ga4),
        from_date=start,
        to_date=end,
        updated_at=source_updated_at,
        share_token=share.share_token if share else None,
        source_error="; ".join(errors) if errors else None,
    )
    db.add(
        KfcMundialSnapshot(
            from_date=start,
            to_date=end,
            payload_json=payload,
            source_updated_at=source_updated_at,
        )
    )
    db.commit()
    return payload


def latest_mundial_snapshot(
    db: Session,
    from_date: date,
    to_date: date,
) -> Optional[KfcMundialSnapshot]:
    return (
        db.query(KfcMundialSnapshot)
        .filter(
            KfcMundialSnapshot.from_date == from_date,
            KfcMundialSnapshot.to_date == to_date,
        )
        .order_by(KfcMundialSnapshot.created_at.desc())
        .first()
    )


def get_active_mundial_share(db: Session) -> Optional[KfcMundialShare]:
    return (
        db.query(KfcMundialShare)
        .filter(KfcMundialShare.revoked_at.is_(None))
        .order_by(KfcMundialShare.shared_at.desc())
        .first()
    )


def create_mundial_share_token(db: Session, user: AuthUser) -> KfcMundialShare:
    existing = get_active_mundial_share(db)
    if existing:
        return existing

    share = KfcMundialShare(
        share_token=secrets.token_urlsafe(32),
        shared_at=utcnow(),
        created_by_oid=user.oid,
        created_by_email=user.email,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def revoke_mundial_share_token(db: Session) -> None:
    active = db.query(KfcMundialShare).filter(KfcMundialShare.revoked_at.is_(None)).all()
    now = utcnow()
    for share in active:
        share.revoked_at = now
    db.commit()


def get_mundial_share_by_token(db: Session, token: str) -> Optional[KfcMundialShare]:
    return (
        db.query(KfcMundialShare)
        .filter(
            KfcMundialShare.share_token == token,
            KfcMundialShare.revoked_at.is_(None),
        )
        .one_or_none()
    )


def _fetch_google_ads(client: WindsorClient, start: date, end: date) -> list[dict]:
    try:
        return _fetch_connector_or_raise(
            client,
            "google_ads",
            MUNDIAL_GOOGLE_ADS_FIELDS,
            start,
            end,
        )
    except WindsorError as primary_exc:
        logger.error(
            "Retrying Windsor connector=google_ads with fallback fields after primary failure: %s",
            primary_exc,
        )
        try:
            return _fetch_connector_or_raise(
                client,
                "google_ads",
                MUNDIAL_GOOGLE_ADS_FALLBACK_FIELDS,
                start,
                end,
                label="google_ads fallback",
            )
        except WindsorError as fallback_exc:
            raise WindsorError(
                "google_ads failed with primary and fallback fields: "
                f"primary={primary_exc}; fallback={fallback_exc}"
            ) from fallback_exc


def _fetch_connector_or_raise(
    client: WindsorClient,
    connector: str,
    fields: list[str],
    start: date,
    end: date,
    *,
    label: Optional[str] = None,
) -> list[dict]:
    connector_label = label or connector
    url = f"{client.base_url}/{connector}"
    logger.info(
        "Fetching Windsor connector=%s url=%s fields=%s date_from=%s date_to=%s",
        connector_label,
        url,
        ",".join(fields),
        start.isoformat(),
        end.isoformat(),
    )
    try:
        rows = client.fetch_connector(connector, fields, start, end)
    except WindsorError as exc:
        logger.error(
            "Windsor connector=%s failed url=%s fields=%s date_from=%s date_to=%s error=%s",
            connector_label,
            url,
            ",".join(fields),
            start.isoformat(),
            end.isoformat(),
            exc,
        )
        raise WindsorError(f"{connector_label} failed: {exc}") from exc

    logger.info(
        "Windsor connector=%s ok rows=%s url=%s fields=%s date_from=%s date_to=%s",
        connector_label,
        len(rows),
        url,
        ",".join(fields),
        start.isoformat(),
        end.isoformat(),
    )
    return rows


def _prepare_mundial_payload(
    db: Session,
    payload: dict,
    *,
    public_token: Optional[str],
) -> dict:
    response = dict(payload)
    if public_token:
        return sanitize_public_mundial_payload(response, public_token)

    share = get_active_mundial_share(db)
    response["shareToken"] = share.share_token if share else None
    response["publicToken"] = None
    return response


def _is_fresh(snapshot: KfcMundialSnapshot, settings: Settings) -> bool:
    updated_at = snapshot.source_updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return updated_at >= utcnow() - timedelta(seconds=settings.cache_ttl_seconds)
