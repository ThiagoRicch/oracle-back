import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from Repository.ServidorRepository import ServidorRepository
from Service.ReportService import ReportService


logger = logging.getLogger(__name__)


def _is_scheduler_enabled() -> bool:
    raw = os.getenv("ENABLE_INTERNAL_SCHEDULER", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.report_service = ReportService(ServidorRepository())
        self.enabled = _is_scheduler_enabled()

    def start(self):
        if not self.enabled:
            logger.info("Scheduler interno desativado via ENABLE_INTERNAL_SCHEDULER")
            return

        if self.scheduler.running:
            return

        self.scheduler.add_job(
            self.report_service.send_daily_reports,
            IntervalTrigger(minutes=1),
            id="daily-report-coordinator",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.add_job(
            self.report_service.send_monthly_reports,
            IntervalTrigger(minutes=1),
            id="monthly-report-coordinator",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.add_job(
            self.report_service.refresh_weather_status,
            IntervalTrigger(minutes=30),
            id="weather-monitor",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()
        logger.info("Scheduler interno iniciado")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler interno finalizado")


scheduler_service = SchedulerService()