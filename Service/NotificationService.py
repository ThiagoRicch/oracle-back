import html
import logging
import mimetypes
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from Service.TimezoneService import TimezoneService


logger = logging.getLogger(__name__)


@dataclass
class EventNotification:
    event_type: str
    description: str
    servidor: dict
    timestamp: datetime
    snapshot: dict | None = None


class NotificationService:
    def __init__(self, timezone_service: TimezoneService | None = None):
        self.timezone_service = timezone_service or TimezoneService()
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_sender = os.getenv("SMTP_SENDER", self.smtp_user or "noreply@pim.local")
        self.smtp_sender_name = os.getenv("SMTP_SENDER_NAME", "Oracle - PIM")

        recipients_env = os.getenv("NOTIFICATION_EMAIL_TO", "") or os.getenv("EMAIL_EVENT_RECIPIENTS", "")
        self.recipients = [recipient.strip() for recipient in recipients_env.split(",") if recipient.strip()]

        self.oracle_logo_url = os.getenv(
            "ORACLE_LOGO_URL",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Oracle_logo.svg/512px-Oracle_logo.svg.png",
        )
        self.oracle_logo_path = Path(os.getenv("ORACLE_LOGO_PATH", "assets/oracle.png"))
        self.oracle_logo_cid = "oracle_logo"

    def send_event_notification(self, notification: EventNotification):
        servidor = notification.servidor or {}
        timezone_name = self.timezone_service.resolve_timezone_name(
            servidor.get("latitude"),
            servidor.get("longitude"),
            servidor.get("continente"),
            servidor.get("pais"),
            servidor.get("cidade"),
        )
        local_timestamp = notification.timestamp.astimezone(
            self.timezone_service.get_timezone(
                servidor.get("latitude"),
                servidor.get("longitude"),
                servidor.get("continente"),
                servidor.get("pais"),
                servidor.get("cidade"),
            )
        )

        body_text = self._build_event_text(notification, servidor, local_timestamp, timezone_name)
        body_html = self._build_event_html(notification, servidor, local_timestamp, timezone_name)

        subject = f"[{notification.event_type}] {servidor.get('nome', 'Servidor')}"
        self._deliver(subject, body_text, body_html)

    def send_report(self, subject: str, body: str):
        html_body = self._build_simple_report_html(subject, body)
        self._deliver(subject, body, html_body)

    def _deliver(self, subject: str, body: str, html_body: str | None = None):
        if not self.recipients or not self.smtp_host:
            logger.warning(
                "Email não enviado. Configure SMTP_HOST e NOTIFICATION_EMAIL_TO. Assunto: %s",
                subject,
            )
            logger.info("Corpo do email não enviado:\n%s", body)
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.smtp_sender_name, self.smtp_sender))
        message["To"] = ", ".join(self.recipients)
        message.set_content(body)

        if html_body:
            message.add_alternative(html_body, subtype="html")
            self._attach_inline_logo(message)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if self.smtp_user and self.smtp_password:
                smtp.login(self.smtp_user, self.smtp_password)
            smtp.send_message(message)

        return True

    def _attach_inline_logo(self, message: EmailMessage):
        if not self.oracle_logo_path.exists() or not self.oracle_logo_path.is_file():
            return

        with self.oracle_logo_path.open("rb") as file:
            logo_bytes = file.read()

        guessed_type, _ = mimetypes.guess_type(str(self.oracle_logo_path))
        subtype = "png"
        if guessed_type and guessed_type.startswith("image/"):
            subtype = guessed_type.split("/")[-1]

        html_part = message.get_payload()[-1]
        html_part.add_related(logo_bytes, maintype="image", subtype=subtype, cid=f"<{self.oracle_logo_cid}>")

    def _logo_source(self):
        if self.oracle_logo_path.exists() and self.oracle_logo_path.is_file():
            return f"cid:{self.oracle_logo_cid}"
        return html.escape(self.oracle_logo_url)

    def _build_event_text(self, notification: EventNotification, servidor: dict, local_timestamp: datetime, timezone_name: str):
        lines = [
            f"Tipo do evento: {notification.event_type}",
            f"Servidor: {servidor.get('nome', 'N/A')}",
            f"País: {servidor.get('pais', 'N/A')}",
            f"Continente: {servidor.get('continente', 'N/A')}",
            f"Bandeira: {servidor.get('bandeira', '-')}",
            f"Timestamp: {local_timestamp.isoformat()} ({timezone_name})",
            "",
            notification.description,
        ]

        snapshot = notification.snapshot or {}
        before = snapshot.get("before") if isinstance(snapshot, dict) else None
        after = snapshot.get("after") if isinstance(snapshot, dict) else None
        context = snapshot.get("context") if isinstance(snapshot, dict) else None

        if before:
            lines.append("\nSnapshot (antes):")
            for key, value in before.items():
                lines.append(f"- {key}: {value}")

        if after:
            lines.append("\nSnapshot (depois):")
            for key, value in after.items():
                lines.append(f"- {key}: {value}")

        if context:
            lines.append("\nContexto:")
            for key, value in context.items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    def _build_event_html(self, notification: EventNotification, servidor: dict, local_timestamp: datetime, timezone_name: str):
        event_rows = [
            ("Tipo do evento", notification.event_type),
            ("Servidor", servidor.get("nome", "N/A")),
            ("País", servidor.get("pais", "N/A")),
            ("Continente", servidor.get("continente", "N/A")),
            ("Bandeira", servidor.get("bandeira", "-")),
            ("Timestamp", f"{local_timestamp.isoformat()} ({timezone_name})"),
            ("Descrição", notification.description),
        ]
        event_table = self._render_table_rows(event_rows)

        snapshot = notification.snapshot if isinstance(notification.snapshot, dict) else {}
        before_table = ""
        after_table = ""
        context_table = ""

        if snapshot.get("before") and isinstance(snapshot.get("before"), dict):
            before_table = self._render_snapshot_section("Snapshot - Antes", snapshot.get("before"))
        if snapshot.get("after") and isinstance(snapshot.get("after"), dict):
            after_table = self._render_snapshot_section("Snapshot - Depois", snapshot.get("after"))
        if snapshot.get("context") and isinstance(snapshot.get("context"), dict):
            context_table = self._render_snapshot_section("Contexto", snapshot.get("context"))

        logo_source = self._logo_source()

        return f"""
<!DOCTYPE html>
<html lang=\"pt-BR\">
  <body style=\"margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;color:#1f2937;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#f4f6f8;padding:24px 0;\">
      <tr>
        <td align=\"center\">
          <table role=\"presentation\" width=\"700\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:700px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;\">
            <tr>
              <td style=\"background:#c74634;padding:20px 24px;\">
                <img src=\"{logo_source}\" alt=\"Oracle\" height=\"28\" style=\"display:block;height:28px;max-width:180px;\" />
              </td>
            </tr>
            <tr>
              <td style=\"padding:24px;\">
                <h2 style=\"margin:0 0 16px 0;font-size:20px;color:#111827;\">Notificação de Evento</h2>
                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;\">
                  <tbody>
                    {event_table}
                  </tbody>
                </table>
                {before_table}
                {after_table}
                {context_table}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    @staticmethod
    def _render_table_rows(rows: list[tuple[str, object]]):
        html_rows = []
        for idx, (label, value) in enumerate(rows):
            background = "#ffffff" if idx % 2 == 0 else "#f9fafb"
            html_rows.append(
                f"""
                <tr style=\"background:{background};\">
                  <td style=\"padding:12px 14px;border-bottom:1px solid #e5e7eb;width:220px;font-weight:bold;color:#374151;\">{html.escape(str(label))}</td>
                  <td style=\"padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827;\">{html.escape(str(value))}</td>
                </tr>
                """
            )
        return "".join(html_rows)

    def _render_snapshot_section(self, title: str, data: dict):
        rows = [(str(key), value) for key, value in data.items()]
        table_rows = self._render_table_rows(rows)
        return f"""
        <h3 style=\"margin:20px 0 10px 0;font-size:16px;color:#111827;\">{html.escape(title)}</h3>
        <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;\">
          <tbody>
            {table_rows}
          </tbody>
        </table>
        """

    def _build_simple_report_html(self, subject: str, body: str):
        escaped_body = html.escape(body).replace("\n", "<br />")
        logo_source = self._logo_source()
        return f"""
<!DOCTYPE html>
<html lang=\"pt-BR\">
  <body style=\"margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;color:#1f2937;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#f4f6f8;padding:24px 0;\">
      <tr>
        <td align=\"center\">
          <table role=\"presentation\" width=\"700\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:700px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;\">
            <tr>
              <td style=\"background:#c74634;padding:20px 24px;\">
                <img src=\"{logo_source}\" alt=\"Oracle\" height=\"28\" style=\"display:block;height:28px;max-width:180px;\" />
              </td>
            </tr>
            <tr>
              <td style=\"padding:24px;\">
                <h2 style=\"margin:0 0 16px 0;font-size:20px;color:#111827;\">{html.escape(subject)}</h2>
                <div style=\"font-size:14px;line-height:1.6;color:#111827;\">{escaped_body}</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    @staticmethod
    def now_utc():
        return datetime.now(timezone.utc)
