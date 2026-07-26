# Tasks: HITECH Email Reminder System

This list consolidates remaining features, technical debt, and system enhancements for the project.

## High Priority
- [ ] **Update README.md**: Rewrite documentation to accurately reflect the FastAPI dashboard, SQLite database usage, WhatsApp integration, and the updated CLI jobs.
- [ ] **Implement Log Rotation**: Switch `logging.FileHandler` to `logging.handlers.RotatingFileHandler` in `src/utils/logger.py` to prevent disk space exhaustion.
- [ ] **HTML Email Templates**: Upgrade `EmailTemplate.build()` to return HTML content and update `GmailEmailSender` to dispatch `MIMEText(body, 'html')`.
- [ ] **Multiple Recipients**: Modify the database schema and settings to allow a comma-separated list of email recipients and handle iterative dispatching.

## Medium Priority
- [ ] **Pagination in Dashboard**: Add pagination to FastAPI routes (`/activities`, `/modules`, `/imports`) in `src/web/app.py` and Jinja2 templates.
- [ ] **Dockerization**: Create a `Dockerfile` and `docker-compose.yml` for isolated execution.
- [ ] **Dependency Pinning**: Replace loose dependencies in `requirements.txt` with exact versions or migrate to `uv` / `poetry` for deterministic builds.
- [ ] **Advance Reminders**: Implement logic to send a "heads-up" reminder X days before a deadline (requires parsing target date offsets).
- [ ] **Escalation Emails**: Track missed activities and implement a system to notify supervisors or escalate priorities.

## Low Priority / Future Enhancements
- [ ] **SMS Reminders**: Integrate Twilio or a local SMS provider.
- [ ] **Microsoft Teams Notifications**: Implement Webhook-based messaging to Teams channels.
- [ ] **Slack Notifications**: Implement Webhook-based messaging to Slack channels.
- [ ] **Holiday Calendar**: Allow skipping reminders or shifting them to the previous/next working day when the due date lands on a public holiday or weekend.
- [x] **Deprecate Dead Code**: Fully remove `src/excel/excel_reader.py` if `src/services/excel_importer.py` provides complete parity.
