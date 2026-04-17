import logging
from calendar import monthrange
from datetime import datetime

from Enum.Continentes import Continentes
from Service.EnergyMonitoringService import EnergyMonitoringService
from Service.NotificationService import NotificationService
from Service.TimezoneService import TimezoneService
from Service.WeatherService import WeatherService


logger = logging.getLogger(__name__)


class ReportService:
    def __init__(
        self,
        servidor_repository,
        notification_service: NotificationService | None = None,
        energy_service: EnergyMonitoringService | None = None,
        weather_service: WeatherService | None = None,
        timezone_service: TimezoneService | None = None,
    ):
        self.repo = servidor_repository
        self.notification_service = notification_service or NotificationService()
        self.energy_service = energy_service or EnergyMonitoringService()
        self.timezone_service = timezone_service or TimezoneService()
        self.weather_service = weather_service or WeatherService(self.timezone_service)
        self.report_registry = {"daily": {}, "monthly": {}}
        self.weather_cache = {}

    def refresh_weather_status(self):
        servers = self.repo.listar_servidores()
        snapshots = {}
        for servidor in servers:
            try:
                snapshots[str(servidor.get("id"))] = self.weather_service.get_weather_snapshot(
                    servidor.get("latitude"),
                    servidor.get("longitude"),
                    servidor.get("continente"),
                )
            except Exception as exc:
                logger.warning(
                    "Falha ao consultar clima do servidor %s: %s",
                    servidor.get("nome"),
                    exc,
                )
                snapshots[str(servidor.get("id"))] = {
                    "solar_active": False,
                    "reason": "Falha ao consultar API de clima",
                    "checked_at": datetime.utcnow().isoformat(),
                }
            self.weather_cache = snapshots
        return snapshots

    def send_daily_reports(self):
        return self._send_reports(report_type="daily")

    def send_monthly_reports(self):
        return self._send_reports(report_type="monthly")

    def _send_reports(self, report_type: str):
        servers = self.repo.listar_servidores()
        weather_map = self.weather_cache or self.refresh_weather_status()
        sent = []

        for continente in Continentes:
            servers_by_continent = [
                servidor for servidor in servers if servidor.get("continente") == continente.value
            ]
            if not servers_by_continent:
                continue

            base_server = servers_by_continent[0]
            timezone_name = self.timezone_service.resolve_timezone_name(
                base_server.get("latitude"),
                base_server.get("longitude"),
                continente.value,
                base_server.get("pais"),
                base_server.get("cidade"),
            )
            local_now = datetime.now(
                self.timezone_service.get_timezone(
                    base_server.get("latitude"),
                    base_server.get("longitude"),
                    continente.value,
                    base_server.get("pais"),
                    base_server.get("cidade"),
                )
            )
            if local_now.hour != 23 or local_now.minute != 50:
                continue

            if report_type == "monthly":
                last_day = monthrange(local_now.year, local_now.month)[1]
                if local_now.day != last_day:
                    continue

            registry_key = f"{continente.value}:{local_now.date().isoformat()}"
            if self.report_registry[report_type].get(registry_key):
                continue

            body = self._build_report_body(
                report_type,
                continente.value,
                servers_by_continent,
                weather_map,
                local_now,
            )
            title = "Relatório Diário" if report_type == "daily" else "Relatório Mensal"
            self.notification_service.send_report(f"{title} - {continente.value}", body)
            self.report_registry[report_type][registry_key] = {
                "sent_at": local_now.isoformat(),
                "timezone": timezone_name,
            }
            sent.append(
                {
                    "continente": continente.value,
                    "timezone": timezone_name,
                    "sent_at": local_now.isoformat(),
                }
            )

        return sent

    def _build_report_body(self, report_type: str, continente: str, servers: list[dict], weather_map: dict, local_now: datetime):
        lines = [
            f"📊 {'Relatório Diário' if report_type == 'daily' else 'Relatório Mensal'} - {continente}",
            f"Gerado em: {local_now.isoformat()}",
            "",
        ]

        for servidor in servers:
            metrics = (
                self.energy_service.build_daily_metrics(servidor, local_now.date())
                if report_type == "daily"
                else self.energy_service.build_monthly_metrics(servidor, local_now.date())
            )
            weather = weather_map.get(str(servidor.get("id")), {})
            lines.extend(
                [
                    f"🖥️ Servidor: {servidor.get('nome', 'N/A')}",
                    f"{servidor.get('bandeira', '')} {servidor.get('pais', 'N/A')}",
                    f"Status: {'Ativo' if servidor.get('status') else 'Inativo'}",
                    f"⚡ Consumo: {metrics['consumption_kwh']} kWh",
                    (
                        f"💰 Custo: {metrics['currency_symbol']}{metrics['local_cost']} {metrics['currency_code']} | "
                        f"${metrics['usd_cost']} USD"
                    ),
                    (
                        "☀️ Energia Solar: Ativada"
                        if weather.get("solar_active")
                        else f"☀️ Energia Solar: Desativada ({weather.get('reason', 'Indisponível')})"
                    ),
                    "------------------------",
                    "",
                ]
            )

        return "\n".join(lines)