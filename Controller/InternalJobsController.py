import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, status

from Service.SchedulerService import scheduler_service


router = APIRouter(prefix="/internal/jobs", tags=["Internal Jobs"])


def _validate_internal_secret(authorization: str | None, x_internal_secret: str | None):
    expected = os.getenv("INTERNAL_CRON_SECRET", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INTERNAL_CRON_SECRET não configurado",
        )

    bearer_secret = ""
    if authorization and authorization.startswith("Bearer "):
        bearer_secret = authorization.replace("Bearer ", "", 1).strip()

    provided = (x_internal_secret or "").strip() or bearer_secret
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")


@router.post("/daily")
def run_daily_job(
    authorization: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
):
    _validate_internal_secret(authorization, x_internal_secret)
    sent = scheduler_service.report_service.send_daily_reports()
    return {
        "job": "daily",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "reports_sent": sent,
        "count": len(sent),
    }


@router.post("/monthly")
def run_monthly_job(
    authorization: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
):
    _validate_internal_secret(authorization, x_internal_secret)
    sent = scheduler_service.report_service.send_monthly_reports()
    return {
        "job": "monthly",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "reports_sent": sent,
        "count": len(sent),
    }


@router.post("/weather")
def run_weather_job(
    authorization: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
):
    _validate_internal_secret(authorization, x_internal_secret)
    weather = scheduler_service.report_service.refresh_weather_status()
    return {
        "job": "weather",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "servers_updated": len(weather),
    }
