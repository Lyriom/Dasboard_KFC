from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.aggregation import isoformat_z
from app.config import Settings, get_settings
from app.constants import BASE_START_DATE
from app.database import get_db, init_db
from app.models import utcnow
from app.mundial import MUNDIAL_START_DATE
from app.mundial_service import (
    MundialDashboardUnavailable,
    create_mundial_share_token,
    get_mundial_dashboard,
    get_mundial_share_by_token,
    normalize_mundial_range,
    refresh_mundial_dashboard,
    revoke_mundial_share_token,
    today_in_mundial_timezone,
)
from app.rate_limit import InMemoryRateLimiter, request_ip
from app.security import AuthUser, require_dashboard_role
from app.service import (
    DashboardUnavailable,
    create_share_token,
    get_dashboard,
    get_share_by_token,
    normalize_range,
    refresh_dashboard,
    revoke_share_token,
    today_in_app_timezone,
)
from app.windsor import WindsorError


settings = get_settings()
rate_limiter = InMemoryRateLimiter(
    settings.public_rate_limit_requests,
    settings.public_rate_limit_window_seconds,
)
scheduler: Optional[BackgroundScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    if settings.create_db_on_startup:
        init_db()
    if settings.scheduler_enabled and settings.refresh_cron:
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            _scheduled_refresh,
            CronTrigger.from_crontab(settings.refresh_cron),
            id="kfc-app-installs-refresh",
            max_instances=1,
            replace_existing=True,
        )
        scheduler.add_job(
            _scheduled_mundial_refresh,
            CronTrigger.from_crontab(settings.refresh_cron),
            id="kfc-mundial-refresh",
            max_instances=1,
            replace_existing=True,
        )
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="KFC Instalaciones App API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "kfc-app-installs"}


@app.get("/api/kfc-app-installs/dashboard")
def dashboard(
    from_date: Annotated[Optional[date], Query(alias="from")] = None,
    to_date: Annotated[Optional[date], Query(alias="to")] = None,
    _: AuthUser = Depends(require_dashboard_role),
    db: Session = Depends(get_db),
    request_settings: Settings = Depends(get_settings),
) -> dict:
    start, end = _validated_range(from_date, to_date, request_settings)
    try:
        return get_dashboard(
            db,
            request_settings,
            from_date=start,
            to_date=end,
            force_refresh=False,
        )
    except DashboardUnavailable as exc:
        return _dashboard_unavailable_response()


@app.get("/api/kfc-mundial/dashboard")
def mundial_dashboard(
    from_date: Annotated[Optional[date], Query(alias="from")] = None,
    to_date: Annotated[Optional[date], Query(alias="to")] = None,
    _: AuthUser = Depends(require_dashboard_role),
    db: Session = Depends(get_db),
    request_settings: Settings = Depends(get_settings),
) -> dict:
    start, end = _validated_mundial_range(from_date, to_date, request_settings)
    try:
        return get_mundial_dashboard(
            db,
            request_settings,
            from_date=start,
            to_date=end,
            force_refresh=False,
        )
    except MundialDashboardUnavailable:
        return _dashboard_unavailable_response()


@app.post("/api/kfc-app-installs/refresh")
def refresh(
    from_date: Annotated[Optional[date], Query(alias="from")] = None,
    to_date: Annotated[Optional[date], Query(alias="to")] = None,
    _: AuthUser = Depends(require_dashboard_role),
    db: Session = Depends(get_db),
    request_settings: Settings = Depends(get_settings),
) -> dict:
    start, end = _validated_range(from_date, to_date, request_settings)
    try:
        payload = refresh_dashboard(db, request_settings, from_date=start, to_date=end)
        response = get_dashboard(
            db,
            request_settings,
            from_date=start,
            to_date=end,
            force_refresh=False,
        )
        response["updatedAt"] = payload["updatedAt"]
        return response
    except WindsorError as exc:
        try:
            return get_dashboard(
                db,
                request_settings,
                from_date=start,
                to_date=end,
                force_refresh=False,
            )
        except DashboardUnavailable:
            return _dashboard_unavailable_response()


@app.post("/api/kfc-mundial/share")
def mundial_share(
    user: AuthUser = Depends(require_dashboard_role),
    db: Session = Depends(get_db),
) -> dict:
    share_row = create_mundial_share_token(db, user)
    return {
        "shareToken": share_row.share_token,
        "sharedAt": isoformat_z(share_row.shared_at),
    }


@app.delete("/api/kfc-mundial/share", status_code=status.HTTP_204_NO_CONTENT)
def mundial_revoke_share(
    _: AuthUser = Depends(require_dashboard_role),
    db: Session = Depends(get_db),
) -> Response:
    revoke_mundial_share_token(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/kfc-app-installs/share")
def share(
    user: AuthUser = Depends(require_dashboard_role),
    db: Session = Depends(get_db),
) -> dict:
    share_row = create_share_token(db, user)
    return {
        "shareToken": share_row.share_token,
        "sharedAt": isoformat_z(share_row.shared_at),
    }


@app.delete("/api/kfc-app-installs/share", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(
    _: AuthUser = Depends(require_dashboard_role),
    db: Session = Depends(get_db),
) -> Response:
    revoke_share_token(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/public/kfc-app-installs/{share_token}")
def public_dashboard(
    share_token: str,
    request: Request,
    from_date: Annotated[Optional[date], Query(alias="from")] = None,
    to_date: Annotated[Optional[date], Query(alias="to")] = None,
    db: Session = Depends(get_db),
    request_settings: Settings = Depends(get_settings),
) -> dict:
    rate_limiter.check(request_ip(request))
    if not get_share_by_token(db, share_token):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    start, end = _validated_range(from_date, to_date, request_settings)
    try:
        return get_dashboard(
            db,
            request_settings,
            from_date=start,
            to_date=end,
            force_refresh=False,
            public=True,
        )
    except DashboardUnavailable as exc:
        return _dashboard_unavailable_response()


@app.get("/api/public/kfc-mundial/{share_token}")
def mundial_public_dashboard(
    share_token: str,
    request: Request,
    from_date: Annotated[Optional[date], Query(alias="from")] = None,
    to_date: Annotated[Optional[date], Query(alias="to")] = None,
    db: Session = Depends(get_db),
    request_settings: Settings = Depends(get_settings),
) -> dict:
    rate_limiter.check(request_ip(request))
    if not get_mundial_share_by_token(db, share_token):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    start, end = _validated_mundial_range(from_date, to_date, request_settings)
    try:
        return get_mundial_dashboard(
            db,
            request_settings,
            from_date=start,
            to_date=end,
            force_refresh=False,
            public_token=share_token,
        )
    except MundialDashboardUnavailable:
        return _dashboard_unavailable_response()


def _validated_range(
    from_date: Optional[date],
    to_date: Optional[date],
    request_settings: Settings,
) -> tuple[date, date]:
    try:
        return normalize_range(from_date, to_date, request_settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _validated_mundial_range(
    from_date: Optional[date],
    to_date: Optional[date],
    request_settings: Settings,
) -> tuple[date, date]:
    try:
        return normalize_mundial_range(from_date, to_date, request_settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _scheduled_refresh() -> None:
    if not settings.windsor_api_key:
        return
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        refresh_dashboard(
            db,
            settings,
            from_date=BASE_START_DATE,
            to_date=today_in_app_timezone(settings),
        )
    finally:
        db.close()


def _scheduled_mundial_refresh() -> None:
    if not settings.windsor_api_key:
        return
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        refresh_mundial_dashboard(
            db,
            settings,
            from_date=MUNDIAL_START_DATE,
            to_date=today_in_mundial_timezone(settings),
        )
    finally:
        db.close()


def _dashboard_unavailable_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "No hay snapshot disponible y Windsor.ai no respondió a tiempo."},
    )
