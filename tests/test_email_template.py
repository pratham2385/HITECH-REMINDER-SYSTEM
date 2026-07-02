"""Tests for reminder email formatting."""

from __future__ import annotations

import unittest
from datetime import date

from src.email.email_template import EmailTemplate
from src.models import Activity


class EmailTemplateTests(unittest.TestCase):
    """Verify the plain-text reminder email body."""

    def test_build_email_contains_all_activities(self) -> None:
        activities = [
            Activity("GST Payment", "Monthly", 20, 2),
            Activity("TDS Payment", "Monthly", 7, 3),
        ]

        content = EmailTemplate.build(activities, date(2026, 6, 26))

        self.assertEqual(content.subject, "Activities Scheduled for Today")
        self.assertIn("1. GST Payment", content.body)
        self.assertIn("2. TDS Payment", content.body)
        self.assertIn("26 June 2026", content.body)

