from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from Repository.ServidorRepository import ServidorRepository
from Service.ReportService import ReportService


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.report_service = ReportService(ServidorRepository())

    def start(self):
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

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)


scheduler_service = SchedulerService()