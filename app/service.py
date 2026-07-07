from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.aggregation import (
    NormalizedDaily,
    aggregate_weekly,
    build_dashboard_payload,
    sanitize_public_dashboard,
)
from app.config import Settings
from app.constants import (
    BASE_START_DATE,
    GOOGLE_FIELDS,
    META_FIELDS,
    TIKTOK_FIELDS,
)
from app.models import (
    KfcAppInstallsDaily,
    KfcAppInstallsShare,
    KfcAppInstallsSnapshot,
    utcnow,
)
from app.security import AuthUser
from app.windsor import WindsorClient, WindsorError
from app.aggregation import normalize_rows


class DashboardUnavailable(RuntimeError):
    pass


def today_in_app_timezone(settings: Settings) -> date:
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def normalize_range(
    from_date: Optional[date],
    to_date: Optional[date],
    settings: Settings,
) -> tuple[date, date]:
    start = from_date or BASE_START_DATE
    end = to_date or today_in_app_timezone(settings)
    if start < BASE_START_DATE:
        start = BASE_START_DATE
    if end < start:
        raise ValueError("to must be greater than or equal to from")
    return start, end


def get_dashboard(
    db: Session,
    settings: Settings,
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    force_refresh: bool = False,
    public: bool = False,
) -> dict:
    start, end = normalize_range(from_date, to_date, settings)

    if not force_refresh:
        snapshot = latest_snapshot(db, start, end)
        if snapshot and _is_fresh(snapshot, settings):
            return _prepare_payload(db, snapshot.payload_json, public=public)

    try:
        payload = refresh_dashboard(db, settings, from_date=start, to_date=end)
        return _prepare_payload(db, payload, public=public)
    except WindsorError as exc:
        snapshot = latest_snapshot(db, start, end)
        if snapshot:
            payload = dict(snapshot.payload_json)
            payload["isStale"] = True
            payload["sourceError"] = "windsor_unavailable"
            return _prepare_payload(db, payload, public=public)

        rows = list_daily_rows(db, start, end)
        if rows:
            payload = _payload_from_rows(
                db,
                rows=rows,
                from_date=start,
                to_date=end,
                updated_at=utcnow(),
                is_stale=True,
                source_error="windsor_unavailable",
            )
            return _prepare_payload(db, payload, public=public)

        raise DashboardUnavailable("No cached dashboard is available") from exc


def refresh_dashboard(
    db: Session,
    settings: Settings,
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> dict:
    start, end = normalize_range(from_date, to_date, settings)
    client = WindsorClient(settings)

    raw_meta = client.fetch_connector("facebook", META_FIELDS, BASE_START_DATE, end)
    raw_tiktok = client.fetch_connector("tiktok", TIKTOK_FIELDS, BASE_START_DATE, end)
    raw_google = client.fetch_connector("google_ads", GOOGLE_FIELDS, BASE_START_DATE, end)

    normalized = [
        *normalize_rows("meta", raw_meta),
        *normalize_rows("tiktok", raw_tiktok),
        *normalize_rows("google", raw_google),
    ]

    upsert_daily_rows(db, normalized)
    rows = list_daily_rows(db, start, end)
    source_updated_at = utcnow()
    payload = _payload_from_rows(
        db,
        rows=rows,
        from_date=start,
        to_date=end,
        updated_at=source_updated_at,
    )
    db.add(
        KfcAppInstallsSnapshot(
            from_date=start,
            to_date=end,
            payload_json=payload,
            source_updated_at=source_updated_at,
        )
    )
    db.commit()
    return payload


def upsert_daily_rows(db: Session, rows: list[NormalizedDaily]) -> None:
    for row in rows:
        existing = (
            db.query(KfcAppInstallsDaily)
            .filter(
                KfcAppInstallsDaily.date == row.date,
                KfcAppInstallsDaily.platform == row.platform,
                KfcAppInstallsDaily.account_id == row.account_id,
                KfcAppInstallsDaily.campaign == row.campaign,
            )
            .one_or_none()
        )
        if existing:
            existing.spend = row.spend
            existing.installs = row.installs
            existing.raw_hash = row.raw_hash
        else:
            db.add(
                KfcAppInstallsDaily(
                    date=row.date,
                    platform=row.platform,
                    account_id=row.account_id,
                    campaign=row.campaign,
                    spend=row.spend,
                    installs=row.installs,
                    raw_hash=row.raw_hash,
                )
            )
    db.flush()


def list_daily_rows(db: Session, from_date: date, to_date: date) -> list[KfcAppInstallsDaily]:
    return (
        db.query(KfcAppInstallsDaily)
        .filter(
            KfcAppInstallsDaily.date >= from_date,
            KfcAppInstallsDaily.date <= to_date,
        )
        .all()
    )


def latest_snapshot(
    db: Session,
    from_date: date,
    to_date: date,
) -> Optional[KfcAppInstallsSnapshot]:
    return (
        db.query(KfcAppInstallsSnapshot)
        .filter(
            KfcAppInstallsSnapshot.from_date == from_date,
            KfcAppInstallsSnapshot.to_date == to_date,
        )
        .order_by(KfcAppInstallsSnapshot.created_at.desc())
        .first()
    )


def get_active_share(db: Session) -> Optional[KfcAppInstallsShare]:
    return (
        db.query(KfcAppInstallsShare)
        .filter(KfcAppInstallsShare.revoked_at.is_(None))
        .order_by(KfcAppInstallsShare.shared_at.desc())
        .first()
    )


def create_share_token(db: Session, user: AuthUser) -> KfcAppInstallsShare:
    existing = get_active_share(db)
    if existing:
        return existing

    share = KfcAppInstallsShare(
        share_token=secrets.token_urlsafe(32),
        shared_at=utcnow(),
        created_by_oid=user.oid,
        created_by_email=user.email,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def revoke_share_token(db: Session) -> None:
    active = db.query(KfcAppInstallsShare).filter(KfcAppInstallsShare.revoked_at.is_(None)).all()
    now = utcnow()
    for share in active:
        share.revoked_at = now
    db.commit()


def get_share_by_token(db: Session, token: str) -> Optional[KfcAppInstallsShare]:
    return (
        db.query(KfcAppInstallsShare)
        .filter(
            KfcAppInstallsShare.share_token == token,
            KfcAppInstallsShare.revoked_at.is_(None),
        )
        .one_or_none()
    )


def _payload_from_rows(
    db: Session,
    *,
    rows: list[KfcAppInstallsDaily],
    from_date: date,
    to_date: date,
    updated_at: datetime,
    is_stale: bool = False,
    source_error: Optional[str] = None,
) -> dict:
    weeks = aggregate_weekly(rows, from_date, to_date)
    share = get_active_share(db)
    return build_dashboard_payload(
        weeks=weeks,
        from_date=from_date,
        to_date=to_date,
        updated_at=updated_at,
        share_token=share.share_token if share else None,
        is_stale=is_stale,
        source_error=source_error,
    )


def _prepare_payload(db: Session, payload: dict, *, public: bool) -> dict:
    response = dict(payload)
    if public:
        return sanitize_public_dashboard(response)
    share = get_active_share(db)
    response["shareToken"] = share.share_token if share else None
    return response


def _is_fresh(snapshot: KfcAppInstallsSnapshot, settings: Settings) -> bool:
    updated_at = snapshot.source_updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return updated_at >= utcnow() - timedelta(seconds=settings.cache_ttl_seconds)
