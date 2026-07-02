"""WhatsApp Business Cloud API sender."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import date

from src.config.settings import Settings
from src.models import Activity, WhatsAppSendResult
from src.utils.helpers import format_run_date


class WhatsAppTemplate:
    """Formats WhatsApp reminder template parameters."""

    @staticmethod
    def activity_list(activities: list[Activity]) -> str:
        """Return a compact numbered activity list."""

        return "\n".join(f"{index}. {activity.activity}" for index, activity in enumerate(activities, start=1))

    @staticmethod
    def parameters(activities: list[Activity], run_date: date) -> list[dict[str, str]]:
        """Return template body parameters for the approved Meta template."""

        return [
            {"type": "text", "text": format_run_date(run_date)},
            {"type": "text", "text": WhatsAppTemplate.activity_list(activities)},
        ]


class WhatsAppSender:
    """Sends template messages through the official WhatsApp Business Cloud API."""

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

    def send_activity_reminder(
        self,
        activities: list[Activity],
        run_date: date,
    ) -> WhatsAppSendResult:
        """Send one WhatsApp template message containing all due activities."""

        validation_error = self._validate_settings()
        if validation_error:
            self.logger.error(validation_error)
            return WhatsAppSendResult(success=False, message=validation_error)

        endpoint = (
            f"{self.settings.whatsapp_graph_api_url.rstrip('/')}/"
            f"{self.settings.whatsapp_phone_number_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": self.settings.whatsapp_recipient_number,
            "type": "template",
            "template": {
                "name": self.settings.whatsapp_template_name,
                "language": {"code": self.settings.whatsapp_language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": WhatsAppTemplate.parameters(activities, run_date),
                    }
                ],
            },
        }

        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            error = f"WhatsApp API rejected the message: HTTP {exc.code} {body}"
            self.logger.error(error)
            return WhatsAppSendResult(success=False, message=error)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            error = f"Network failure while sending WhatsApp message: {exc}"
            self.logger.error(error)
            return WhatsAppSendResult(success=False, message=error)

        provider_message_id = None
        messages = response_body.get("messages") if isinstance(response_body, dict) else None
        if messages and isinstance(messages, list):
            provider_message_id = messages[0].get("id")

        success = "WhatsApp reminder sent successfully"
        self.logger.info("%s | recipient=%s", success, self.settings.whatsapp_recipient_number)
        return WhatsAppSendResult(success=True, message=success, provider_message_id=provider_message_id)

    def _validate_settings(self) -> str | None:
        if not self.settings.whatsapp_enabled:
            return "WhatsApp notifications are disabled."

        missing = []
        if not self.settings.whatsapp_access_token:
            missing.append("WHATSAPP_ACCESS_TOKEN")
        if not self.settings.whatsapp_phone_number_id:
            missing.append("WHATSAPP_PHONE_NUMBER_ID")
        if not self.settings.whatsapp_recipient_number:
            missing.append("WHATSAPP_RECIPIENT_NUMBER")
        if not self.settings.whatsapp_template_name:
            missing.append("WHATSAPP_TEMPLATE_NAME")

        if missing:
            return f"Missing required WhatsApp configuration: {', '.join(missing)}"
        return None

