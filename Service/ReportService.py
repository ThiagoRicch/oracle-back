import html as html_module
import logging
import os
from calendar import monthrange
from datetime import datetime, timedelta

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
        self.weather_cache: dict = {}
        self.country_weather_cache: dict = {}

    # ─── Weather ──────────────────────────────────────────────────────────────

    def refresh_weather_status(self):
        """Refreshes weather for every active server AND every country in the enum."""
        servers = self.repo.listar_servidores()
        server_snapshots: dict = {}
        for servidor in servers:
            try:
                server_snapshots[str(servidor.get("id"))] = self.weather_service.get_weather_snapshot(
                    servidor.get("latitude"),
                    servidor.get("longitude"),
                    servidor.get("continente"),
                )
            except Exception as exc:
                logger.warning("Falha ao consultar clima do servidor %s: %s", servidor.get("nome"), exc)
                server_snapshots[str(servidor.get("id"))] = {
                    "solar_active": False,
                    "reason": "Falha ao consultar API de clima",
                    "checked_at": datetime.utcnow().isoformat(),
                }
        self.weather_cache = server_snapshots

        country_snapshots: dict = {}
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

    # ─── Public entry-points ──────────────────────────────────────────────────

    def send_daily_reports(self):
        return self._send_reports(report_type="daily")

    def send_monthly_reports(self):
        return self._send_reports(report_type="monthly")

    def send_solar_decision_reports(self):
        return self._send_solar_decisions()

    # ─── Report dispatch ──────────────────────────────────────────────────────

    def _send_reports(self, report_type: str):
        servers = self.repo.listar_servidores()

        # Ensure weather cache is populated
        if not self.weather_cache:
            self.refresh_weather_status()
        weather_map = self.weather_cache

        sent = []

        # Group only ACTIVE servers by country
        servers_by_country: dict[str, list[dict]] = {}
        for servidor in servers:
            pais = (servidor.get("pais") or "").strip()
            if not pais:
                continue
            if servidor.get("status") is not True:
                continue
            servers_by_country.setdefault(pais, []).append(servidor)

        for pais, country_servers in servers_by_country.items():
            if not country_servers:
                continue

            base_server = country_servers[0]
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

            # Janela ampla ancorada em 23:50 local: 23:20 ate 00:10
            # (50 minutos totais — absorve throttling do GitHub Actions e
            # cold start do Render). Como a janela cruza a meia-noite,
            # calculamos o target_time correto dependendo da hora local:
            #   - hora >= 12 (final do dia): target = HOJE 23:50
            #   - hora  < 12 (madrugada):    target = ONTEM 23:50
            # report_date sempre referente ao target, para idempotencia
            # estavel mesmo quando o envio cai apos a meia-noite.
            if local_now.hour >= 12:
                target_time = local_now.replace(hour=23, minute=50, second=0, microsecond=0)
            else:
                target_time = (local_now - timedelta(days=1)).replace(
                    hour=23, minute=50, second=0, microsecond=0,
                )
            window_start = target_time - timedelta(minutes=30)
            window_end = target_time + timedelta(minutes=20)
            if local_now < window_start or local_now > window_end:
                continue

            report_date = target_time.date().isoformat()

            if report_type == "monthly":
                last_day = monthrange(target_time.year, target_time.month)[1]
                if target_time.day != last_day:
                    continue

            registry_key = f"{pais}:{report_date}"
            if self._report_already_sent(report_type, pais, report_date, registry_key):
                continue

            html_body = self._build_report_html(report_type, pais, country_servers, weather_map, local_now)
            title = "Relatorio Diario" if report_type == "daily" else "Relatorio Mensal"
            self.notification_service.send_report(f"{title} - {pais}", html_body)
            self._mark_report_as_sent(report_type, pais, report_date, timezone_name, local_now.isoformat(), registry_key)
            sent.append({"pais": pais, "timezone": timezone_name, "sent_at": local_now.isoformat()})

        return sent

    def _send_solar_decisions(self):
        decision_hour = int(os.getenv("SOLAR_DECISION_HOUR", "6"))
        decision_minute = int(os.getenv("SOLAR_DECISION_MINUTE", "0"))
        decision_hour = max(0, min(23, decision_hour))
        decision_minute = max(0, min(59, decision_minute))

        sent = []

        # Only send for countries that have at least one ACTIVE server
        all_servers = self.repo.listar_servidores()
        countries_with_active_servers = {
            (s.get("pais") or "").strip()
            for s in all_servers
            if (s.get("pais") or "").strip() and s.get("status") is True
        }

        for continente, paises in PAISES.items():
            for pais in paises:
                if pais.nome not in countries_with_active_servers:
                    continue
                if not pais.localizacoes:
                    continue

                location = pais.localizacoes[0]
                cidade = location.get("cidade")
                latitude = location.get("latitude")
                longitude = location.get("longitude")

                timezone_name = self.timezone_service.resolve_timezone_name(
                    latitude, longitude, continente.value, pais.nome, cidade,
                )
                local_now = datetime.now(
                    self.timezone_service.get_timezone(
                        latitude, longitude, continente.value, pais.nome, cidade,
                    )
                )

                # Janela ampla ancorada no horario de decisao (padrao 06:00):
                # 30 min antes ate 30 min depois — cruza a fronteira de hora
                # com seguranca (ex.: 05:40 ate 06:30). target_time sempre
                # referente ao dia de HOJE local, pois a decisao de ativar
                # energia solar e tomada a cada manha local.
                target_time = local_now.replace(
                    hour=decision_hour, minute=decision_minute, second=0, microsecond=0,
                )
                window_start = target_time - timedelta(minutes=30)
                window_end = target_time + timedelta(minutes=30)
                if local_now < window_start or local_now > window_end:
                    continue

                report_date = target_time.date().isoformat()
                country_key = f"PAIS:{pais.nome}"
                fallback_key = f"solar:{country_key}:{report_date}"
                if self._report_already_sent("solar", country_key, report_date, fallback_key):
                    continue

                try:
                    weather = self.weather_service.get_weather_snapshot(latitude, longitude, continente.value)
                except Exception as exc:
                    logger.warning("Falha ao consultar clima para decisao solar em %s: %s", pais.nome, exc)
                    weather = {
                        "solar_active": False,
                        "is_sunny": False,
                        "weather_code": None,
                        "reason": "Falha ao consultar API de clima",
                    }

                html_body = self._build_solar_decision_html(
                    continente.value, pais.nome, local_now, timezone_name, weather, decision_hour, decision_minute,
                )
                self.notification_service.send_report(f"Decisao Energetica Solar - {pais.nome}", html_body)
                self._mark_report_as_sent("solar", country_key, report_date, timezone_name, local_now.isoformat(), fallback_key)
                sent.append({
                    "continente": continente.value,
                    "pais": pais.nome,
                    "timezone": timezone_name,
                    "sent_at": local_now.isoformat(),
                    "solar_active": bool(weather.get("solar_active")),
                })

        return sent

    # ─── Idempotency ──────────────────────────────────────────────────────────

    def _report_already_sent(self, report_type: str, continente: str, report_date: str, fallback_key: str):
        try:
            return self.repo.report_already_sent(report_type, continente, report_date)
        except Exception:
            return bool(self.report_registry_fallback[report_type].get(fallback_key))

    def _mark_report_as_sent(self, report_type, continente, report_date, timezone_name, sent_at_iso, fallback_key):
        try:
            inserted = self.repo.mark_report_sent(report_type, continente, report_date, timezone_name, sent_at_iso)
            if not inserted:
                logger.info("Relatorio ja registrado para %s/%s em %s", report_type, continente, report_date)
        except Exception:
            self.report_registry_fallback[report_type][fallback_key] = {
                "sent_at": sent_at_iso,
                "timezone": timezone_name,
            }
            logger.warning(
                "Fallback de idempotencia em memoria ativado para %s/%s em %s",
                report_type, continente, report_date,
            )

    # ─── HTML helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _table_row(label: str, value: str, idx: int, value_is_html: bool = False) -> str:
        bg = "#ffffff" if idx % 2 == 0 else "#f9fafb"
        safe_value = value if value_is_html else html_module.escape(str(value))
        return (
            f'<tr style="background:{bg};">'
            f'<td style="padding:11px 16px;border-bottom:1px solid #e5e7eb;width:220px;'
            f'font-weight:600;color:#374151;font-size:13px;white-space:nowrap;">'
            f'{html_module.escape(label)}</td>'
            f'<td style="padding:11px 16px;border-bottom:1px solid #e5e7eb;'
            f'color:#111827;font-size:13px;">{safe_value}</td>'
            f'</tr>'
        )

    @staticmethod
    def _section_header(title: str) -> str:
        return (
            f'<h3 style="margin:28px 0 10px;font-size:14px;font-weight:700;'
            f'color:#374151;text-transform:uppercase;letter-spacing:.05em;'
            f'border-left:3px solid #c74634;padding-left:10px;">'
            f'{html_module.escape(title)}</h3>'
        )

    def _email_wrapper(self, title: str, content: str) -> str:
        logo_src = self.notification_service._logo_source()
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background:#f0f2f5;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="680" cellspacing="0" cellpadding="0"
               style="max-width:680px;width:100%;background:#ffffff;border-radius:12px;
                      overflow:hidden;border:1px solid #d1d5db;
                      box-shadow:0 4px 16px rgba(0,0,0,.08);">

          <!-- Header -->
          <tr>
            <td style="background:#c74634;padding:24px 32px;">
              <img src="{logo_src}" alt="Oracle"
                   height="72" style="display:block;height:72px;width:auto;" />
            </td>
          </tr>

          <!-- Title bar -->
          <tr>
            <td style="background:#1c1c1e;padding:16px 32px;">
              <p style="margin:0;font-size:17px;font-weight:700;
                        color:#ffffff;letter-spacing:.01em;">{html_module.escape(title)}</p>
            </td>
          </tr>

          <!-- Content -->
          <tr>
            <td style="padding:28px 32px 32px;">
              {content}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:16px 32px;background:#f9fafb;
                       border-top:1px solid #e5e7eb;">
              <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center;">
                Oracle Platform Infrastructure Monitor
                &nbsp;&middot;&nbsp;
                Relatorio gerado automaticamente. Nao responda este e-mail.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # ─── Report HTML builder ──────────────────────────────────────────────────

    def _build_report_html(
        self,
        report_type: str,
        pais: str,
        servers: list[dict],
        weather_map: dict,
        local_now: datetime,
    ) -> str:
        title_type = "Relatorio Diario" if report_type == "daily" else "Relatorio Mensal"
        period = local_now.strftime("%d/%m/%Y")
        generated_at = local_now.strftime("%d/%m/%Y %H:%M")

        total_kwh = 0.0
        total_local_cost = 0.0
        total_usd_cost = 0.0
        currency_symbol = "$"
        currency_code = "USD"

        server_blocks = ""
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
            solar_active = bool(weather.get("solar_active"))
            solar_color = "#16a34a" if solar_active else "#dc2626"
            solar_label = "Ativada" if solar_active else f"Desativada — {weather.get('reason', 'Indisponível')}"

            status_ok = bool(servidor.get("status"))
            status_color = "#16a34a" if status_ok else "#dc2626"
            status_label = "Ativo" if status_ok else "Inativo"

            bandeira = servidor.get("bandeira") or ""
            pais_label = f"{bandeira} {servidor.get('pais', 'N/A')}".strip()

            rows = [
                ("Pais", pais_label),
                ("Continente", servidor.get("continente", "N/A")),
                ("Status", f'<span style="color:{status_color};font-weight:700;">{html_module.escape(status_label)}</span>'),
                ("Consumo de Energia", f"{metrics['consumption_kwh']} kWh"),
                ("Custo Local", f"{metrics['currency_symbol']}{metrics['local_cost']} {metrics['currency_code']}"),
                ("Custo em USD", f"$ {metrics['usd_cost']} USD"),
                ("Energia Solar", f'<span style="color:{solar_color};">{html_module.escape(solar_label)}</span>'),
            ]

            rows_html = "".join(
                self._table_row(label, value, i, value_is_html=(label in ("Status", "Energia Solar")))
                for i, (label, value) in enumerate(rows)
            )

            server_blocks += (
                self._section_header(servidor.get("nome", "Servidor"))
                + f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
                  f'style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">'
                  f'<tbody>{rows_html}</tbody></table>'
            )

        # Summary
        summary_rows = [
            ("Consumo Total do Pais", f"{round(total_kwh, 2)} kWh"),
            ("Custo Total Local", f"{currency_symbol}{round(total_local_cost, 2)} {currency_code}"),
            ("Custo Total em USD", f"$ {round(total_usd_cost, 2)} USD"),
        ]
        summary_rows_html = "".join(
            self._table_row(label, value, i) for i, (label, value) in enumerate(summary_rows)
        )
        summary_block = (
            self._section_header("Resumo do Pais")
            + f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
              f'style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">'
              f'<tbody>{summary_rows_html}</tbody></table>'
        )

        meta = (
            f'<p style="margin:0 0 20px;font-size:12px;color:#6b7280;">'
            f'Gerado em {html_module.escape(generated_at)}'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;Periodo: {html_module.escape(period)}</p>'
        )

        content = meta + server_blocks + summary_block
        title = f"{title_type} — {pais}"
        return self._email_wrapper(title, content)

    # ─── Solar decision HTML builder ──────────────────────────────────────────

    def _build_solar_decision_html(
        self,
        continente: str,
        pais: str,
        local_now: datetime,
        timezone_name: str,
        weather: dict,
        decision_hour: int,
        decision_minute: int,
    ) -> str:
        solar_active = bool(weather.get("solar_active"))
        is_sunny = bool(weather.get("is_sunny"))
        weather_code = weather.get("weather_code")
        reason = weather.get("reason", "Motivo nao informado")
        schedule_label = f"{decision_hour:02d}:{decision_minute:02d}"

        condition_label = (
            "Ensolarado — incidencia solar suficiente"
            if is_sunny
            else "Nublado/Chuvoso ou sem incidencia solar suficiente"
        )

        # Find the flag emoji for the country
        bandeira = ""
        for _continente, _paises in PAISES.items():
            for p in _paises:
                if p.nome == pais and p.localizacoes:
                    from Repository.ServidorRepository import ServidorRepository
                    bandeira = ServidorRepository._country_name_to_flag(pais)
                    break

        pais_label = f"{bandeira} {pais}".strip() if bandeira else pais

        info_rows = [
            ("Pais", pais_label),
            ("Continente", continente),
            ("Horario Local de Decisao", schedule_label),
            ("Horario Local da Analise", f"{local_now.isoformat()} ({timezone_name})"),
            ("Condicao Climatica", condition_label),
            ("Codigo Meteorologico", str(weather_code) if weather_code is not None else "N/A"),
            ("Motivo Tecnico", reason),
        ]
        rows_html = "".join(
            self._table_row(label, value, i) for i, (label, value) in enumerate(info_rows)
        )

        if solar_active:
            decision_text = f"{schedule_label} em {pais}: Sera ativado o uso de energia solar."
            box_bg = "#f0fdf4"
            box_border = "#16a34a"
            box_color = "#14532d"
            box_label_bg = "#dcfce7"
            box_label_color = "#166534"
            box_label = "ENERGIA SOLAR ATIVADA"
        else:
            decision_text = (
                f"{schedule_label} em {pais}: Nao sera ativado o uso de energia solar; "
                f"energia eletrica sera usada como padrao."
            )
            box_bg = "#fff7ed"
            box_border = "#ea580c"
            box_color = "#7c2d12"
            box_label_bg = "#ffedd5"
            box_label_color = "#9a3412"
            box_label = "ENERGIA SOLAR NAO ATIVADA"

        decision_box = (
            f'<div style="margin-top:28px;padding:20px 24px;background:{box_bg};'
            f'border:1px solid {box_border};border-radius:10px;">'
            f'<span style="display:inline-block;padding:3px 10px;border-radius:4px;'
            f'background:{box_label_bg};color:{box_label_color};'
            f'font-size:11px;font-weight:700;letter-spacing:.06em;margin-bottom:10px;">'
            f'{box_label}</span>'
            f'<p style="margin:0;font-size:14px;color:{box_color};font-weight:600;line-height:1.5;">'
            f'{html_module.escape(decision_text)}</p>'
            f'</div>'
        )

        content = (
            self._section_header("Informacoes da Decisao")
            + f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
              f'style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">'
              f'<tbody>{rows_html}</tbody></table>'
            + decision_box
        )

        title = f"Decisao Energetica Solar — {pais}"
        return self._email_wrapper(title, content)
