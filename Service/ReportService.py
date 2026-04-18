import logging
import os
from calendar import monthrange
from datetime import datetime

from Enum.Pais import PAISES
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
        self.report_registry_fallback = {"daily": {}, "monthly": {}, "solar": {}}
        self.weather_cache = {}
        self.country_weather_cache = {}

    def refresh_weather_status(self):
        servers = self.repo.listar_servidores()
        server_snapshots = {}
        for servidor in servers:
            try:
                server_snapshots[str(servidor.get("id"))] = self.weather_service.get_weather_snapshot(
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
                server_snapshots[str(servidor.get("id"))] = {
                    "solar_active": False,
                    "reason": "Falha ao consultar API de clima",
                    "checked_at": datetime.utcnow().isoformat(),
                }
        self.weather_cache = server_snapshots

        country_snapshots = {}
        for continente, paises in PAISES.items():
            for pais in paises:
                if not pais.localizacoes:
                    continue
                location = pais.localizacoes[0]
                try:
                    country_snapshots[pais.nome] = self.weather_service.get_weather_snapshot(
                        location.get("latitude"),
                        location.get("longitude"),
                        continente.value,
                    )
                except Exception as exc:
                    logger.warning("Falha ao consultar clima de %s: %s", pais.nome, exc)
                    country_snapshots[pais.nome] = {
                        "solar_active": False,
                        "reason": "Falha ao consultar API de clima",
                        "checked_at": datetime.utcnow().isoformat(),
                    }
        self.country_weather_cache = country_snapshots

        return {"servers": server_snapshots, "countries": country_snapshots}

    def send_daily_reports(self):
        return self._send_reports(report_type="daily")

    def send_monthly_reports(self):
        return self._send_reports(report_type="monthly")

    def send_solar_decision_reports(self):
        return self._send_solar_decisions()

    def _send_reports(self, report_type: str):
        servers = self.repo.listar_servidores()
        weather_map = self.weather_cache or self.refresh_weather_status()
        sent = []

        servers_by_country: dict[str, list[dict]] = {}
        for servidor in servers:
            pais = (servidor.get("pais") or "").strip()
            if not pais:
                continue
            servers_by_country.setdefault(pais, []).append(servidor)

        for pais, servers_by_country_group in servers_by_country.items():
            if not servers_by_country_group:
                continue

            base_server = servers_by_country_group[0]
            timezone_name = self.timezone_service.resolve_timezone_name(
                base_server.get("latitude"),
                base_server.get("longitude"),
                base_server.get("continente"),
                base_server.get("pais"),
                base_server.get("cidade"),
            )
            local_now = datetime.now(
                self.timezone_service.get_timezone(
                    base_server.get("latitude"),
                    base_server.get("longitude"),
                    base_server.get("continente"),
                    base_server.get("pais"),
                    base_server.get("cidade"),
                )
            )
            if local_now.hour != 23 or not (48 <= local_now.minute <= 52):
                continue

            if report_type == "monthly":
                last_day = monthrange(local_now.year, local_now.month)[1]
                if local_now.day != last_day:
                    continue

            report_date = local_now.date().isoformat()
            registry_key = f"{pais}:{report_date}"
            if self._report_already_sent(report_type, pais, report_date, registry_key):
                continue

            body = self._build_report_body(
                report_type,
                pais,
                servers_by_country_group,
                weather_map,
                local_now,
            )
            title = "Relatório Diário" if report_type == "daily" else "Relatório Mensal"
            self.notification_service.send_report(f"{title} - {pais}", body)
            self._mark_report_as_sent(
                report_type,
                pais,
                report_date,
                timezone_name,
                local_now.isoformat(),
                registry_key,
            )
            sent.append(
                {
                    "pais": pais,
                    "timezone": timezone_name,
                    "sent_at": local_now.isoformat(),
                }
            )

        return sent

    def _send_solar_decisions(self):
        decision_hour = int(os.getenv("SOLAR_DECISION_HOUR", "6"))
        decision_minute = int(os.getenv("SOLAR_DECISION_MINUTE", "0"))
        decision_hour = max(0, min(23, decision_hour))
        decision_minute = max(0, min(59, decision_minute))

        sent = []

        servers = self.repo.listar_servidores()
        countries_with_servers = {
            (servidor.get("pais") or "").strip()
            for servidor in servers
            if (servidor.get("pais") or "").strip()
        }

        for continente, paises in PAISES.items():
            for pais in paises:
                if pais.nome not in countries_with_servers:
                    continue
                if not pais.localizacoes:
                    continue

                location = pais.localizacoes[0]
                cidade = location.get("cidade")
                latitude = location.get("latitude")
                longitude = location.get("longitude")

                timezone_name = self.timezone_service.resolve_timezone_name(
                    latitude,
                    longitude,
                    continente.value,
                    pais.nome,
                    cidade,
                )
                local_now = datetime.now(
                    self.timezone_service.get_timezone(
                        latitude,
                        longitude,
                        continente.value,
                        pais.nome,
                        cidade,
                    )
                )

                if local_now.hour != decision_hour or abs(local_now.minute - decision_minute) > 2:
                    continue

                report_date = local_now.date().isoformat()
                country_key = f"PAIS:{pais.nome}"
                fallback_key = f"solar:{country_key}:{report_date}"
                if self._report_already_sent("solar", country_key, report_date, fallback_key):
                    continue

                try:
                    weather = self.weather_service.get_weather_snapshot(
                        latitude,
                        longitude,
                        continente.value,
                    )
                except Exception as exc:
                    logger.warning("Falha ao consultar clima para decisao solar em %s: %s", pais.nome, exc)
                    weather = {
                        "solar_active": False,
                        "is_sunny": False,
                        "weather_code": None,
                        "reason": "Falha ao consultar API de clima",
                    }

                body = self._build_solar_decision_body(
                    continente.value,
                    pais.nome,
                    local_now,
                    timezone_name,
                    weather,
                    decision_hour,
                    decision_minute,
                )
                self.notification_service.send_report(
                    f"Decisao Energetica Solar - {pais.nome}",
                    body,
                )
                self._mark_report_as_sent(
                    "solar",
                    country_key,
                    report_date,
                    timezone_name,
                    local_now.isoformat(),
                    fallback_key,
                )

                sent.append(
                    {
                        "continente": continente.value,
                        "pais": pais.nome,
                        "timezone": timezone_name,
                        "sent_at": local_now.isoformat(),
                        "solar_active": bool(weather.get("solar_active")),
                    }
                )

        return sent

    def _report_already_sent(self, report_type: str, continente: str, report_date: str, fallback_key: str):
        try:
            return self.repo.report_already_sent(report_type, continente, report_date)
        except Exception:
            return bool(self.report_registry_fallback[report_type].get(fallback_key))

    def _mark_report_as_sent(
        self,
        report_type: str,
        continente: str,
        report_date: str,
        timezone_name: str,
        sent_at_iso: str,
        fallback_key: str,
    ):
        try:
            inserted = self.repo.mark_report_sent(
                report_type,
                continente,
                report_date,
                timezone_name,
                sent_at_iso,
            )
            if not inserted:
                logger.info(
                    "Relatório já registrado para %s/%s em %s",
                    report_type,
                    continente,
                    report_date,
                )
        except Exception:
            self.report_registry_fallback[report_type][fallback_key] = {
                "sent_at": sent_at_iso,
                "timezone": timezone_name,
            }
            logger.warning(
                "Fallback de idempotência em memória ativado para %s/%s em %s",
                report_type,
                continente,
                report_date,
            )

    def _build_report_body(self, report_type: str, pais: str, servers: list[dict], weather_map: dict, local_now: datetime):
        lines = [
            f"📊 {'Relatório Diário' if report_type == 'daily' else 'Relatório Mensal'} - {pais}",
            f"Gerado em: {local_now.isoformat()}",
            "",
        ]

        total_kwh = 0.0
        total_local_cost = 0.0
        total_usd_cost = 0.0
        currency_symbol = "$"
        currency_code = "USD"

        for servidor in servers:
            metrics = (
                self.energy_service.build_daily_metrics(servidor, local_now.date())
                if report_type == "daily"
                else self.energy_service.build_monthly_metrics(servidor, local_now.date())
            )
            total_kwh += metrics["consumption_kwh"]
            total_local_cost += metrics["local_cost"]
            total_usd_cost += metrics["usd_cost"]
            currency_symbol = metrics["currency_symbol"]
            currency_code = metrics["currency_code"]

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

        lines.extend(
            [
                "📌 RESUMO DO PAÍS",
                f"⚡ Consumo total do país: {round(total_kwh, 2)} kWh",
                f"💰 Custo total local: {currency_symbol}{round(total_local_cost, 2)} {currency_code}",
                f"💵 Custo total em USD: ${round(total_usd_cost, 2)} USD",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _build_solar_decision_body(
        continente: str,
        pais: str,
        local_now: datetime,
        timezone_name: str,
        weather: dict,
        decision_hour: int,
        decision_minute: int,
    ):
        solar_active = bool(weather.get("solar_active"))
        is_sunny = bool(weather.get("is_sunny"))
        weather_code = weather.get("weather_code")
        reason = weather.get("reason", "Motivo não informado")

        schedule_label = f"{decision_hour:02d}:{decision_minute:02d}"

        if solar_active:
            decision_text = "Será ativado o uso de energia solar."
        else:
            decision_text = "Não será ativado o uso de energia solar; energia elétrica será usada como padrão."

        if is_sunny:
            condition_text = "Condição climática atual: ensolarado."
        else:
            condition_text = "Condição climática atual: nublado/chuvoso ou sem incidência solar suficiente."

        lines = [
            "Relatório Técnico - Decisão Diária de Energia Solar",
            f"País: {pais}",
            f"Continente: {continente}",
            f"Horário local de decisão: {schedule_label}",
            f"Horário local da análise: {local_now.isoformat()} ({timezone_name})",
            condition_text,
            f"Código meteorológico: {weather_code}",
            f"Motivo técnico: {reason}",
            "",
            f"{schedule_label} da manhã em {pais}: {decision_text}",
        ]

        return "\n".join(lines)