"""Email subject and body formatting."""

from __future__ import annotations

from datetime import date

from src.config.settings import APP_NAME
from src.models import Activity, EmailContent
from src.utils.helpers import format_run_date

class EmailTemplate:
    """Builds professional reminder emails."""

    @staticmethod
    def build(recipient: str | list[str], activities: list[Activity], run_date: date | None = None) -> EmailContent:
        """Generate subject and HTML body for the due activities."""
        effective_date = run_date or date.today()
        subject = "Activities Scheduled for Today"

        if not activities:
            return EmailContent(recipient=recipient, subject=subject, body="No activities due today.")

        html = [
            "<html>",
            "<head><style>",
            "table { border-collapse: collapse; width: 100%; font-family: sans-serif; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            "</style></head>",
            "<body>",
            "<h2>The following activities are scheduled for today (" + format_run_date(effective_date) + "):</h2>",
            "<table>",
            "<tr><th>Activity</th><th>Frequency</th><th>Remark</th><th>Link</th></tr>"
        ]
        
        for record in sorted(activities, key=lambda a: a.sort_order if getattr(a, 'sort_order', None) is not None else 0):
            html.append("<tr>")
            html.append(f"<td>{record.activity}</td>")
            html.append(f"<td>{record.frequency}</td>")
            html.append(f"<td>{getattr(record, 'remark', '') or ''}</td>")
            link_html = f"<a href='{record.link}'>View</a>" if getattr(record, 'link', None) else ""
            html.append(f"<td>{link_html}</td>")
            html.append("</tr>")

        html.append("</table>")
        html.append("<p>Please review and complete them.</p>")
        html.append(f"<p>Regards,<br>{APP_NAME}</p>")
        html.append("</body></html>")
        
        return EmailContent(recipient=recipient, subject=subject, body="\n".join(html))
