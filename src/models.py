"""Domain models used by the reminder system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Activity:
    """Represents one activity row loaded from the Excel workbook."""

    activity: str
    frequency: str
    date_value: Any
    row_number: int
    assigned_user_id: int | None = None
    assigned_user_email: str | None = None
    assigned_user_name: str | None = None


@dataclass(frozen=True, slots=True)
class EmailContent:
    """Email subject and body generated for a reminder."""

    recipient: str | list[str]
    subject: str
    body: str


@dataclass(frozen=True, slots=True)
class EmailSendResult:
    """Result returned by an email sender implementation."""

    success: bool
    message: str


@dataclass(frozen=True, slots=True)
class WhatsAppSendResult:
    """Result returned by a WhatsApp sender implementation."""

    success: bool
    message: str
    provider_message_id: str | None = None
