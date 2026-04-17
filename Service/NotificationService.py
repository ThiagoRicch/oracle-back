import json
import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage

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
        recipients_env = os.getenv("NOTIFICATION_EMAIL_TO", "") or os.getenv("EMAIL_EVENT_RECIPIENTS", "")
        self.recipients = [
            recipient.strip()
            for recipient in recipients_env.split(",")
            if recipient.strip()
        ]

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

        if notification.snapshot:
            lines.extend(
                [
                    "",
                    "Snapshot:",
                    json.dumps(notification.snapshot, ensure_ascii=False, indent=2, default=str),
                ]
            )

        subject = f"[{notification.event_type}] {servidor.get('nome', 'Servidor')}"
        self._deliver(subject, "\n".join(lines))

    def send_report(self, subject: str, body: str):
        self._deliver(subject, body)

    def _deliver(self, subject: str, body: str):
        if not self.recipients or not self.smtp_host:
            logger.warning(
                "Email não enviado. Configure SMTP_HOST e NOTIFICATION_EMAIL_TO. Assunto: %s",
                subject,
            )
            logger.info("Corpo do email não enviado:\n%s", body)
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.smtp_sender
        message["To"] = ", ".join(self.recipients)
        message.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if self.smtp_user and self.smtp_password:
                smtp.login(self.smtp_user, self.smtp_password)
            smtp.send_message(message)

        return True

    @staticmethod
    def now_utc():
        return datetime.now(timezone.utc)