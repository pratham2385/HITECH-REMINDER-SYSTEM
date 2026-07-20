# AI Context: HITECH Email Reminder System

This document provides context for the next AI agent taking over the project. The system has evolved from a simple Excel-parsing script to a FastAPI-driven monolithic application with SQLite persistence.

## File Categorization and Status

### Fully Implemented
*   `src/main.py` - Entry point wrapping `send_daily_reminders.py`.
*   `src/models.py` - Core dataclasses (`Activity`, `EmailContent`, `EmailSendResult`, `WhatsAppSendResult`).
*   `src/security.py` - Password hashing (`pbkdf2_sha256`) and signed cookie session logic.
*   `src/config/settings.py` - Environment configuration with fallback defaults.
*   `src/db/models.py` - Comprehensive SQLAlchemy ORM schema.
*   `src/db/session.py` - SQLite engine setup and transaction management context managers.
*   `src/email/email_sender.py` - SMTP mail dispatching logic.
*   `src/email/email_template.py` - Plain-text email composition.
*   `src/excel/excel_reader.py` - Basic script-based Excel reader using pandas.
*   `src/jobs/import_excel.py` - CLI for Excel ingestion.
*   `src/jobs/run_dashboard.py` - CLI for launching Uvicorn server.
*   `src/jobs/send_daily_reminders.py` - CLI to orchestrate email & WhatsApp sending.
*   `src/scheduler/schedule_checker.py` - Logic for date matching (Daily, Monthly, Quarterly, Yearly).
*   `src/services/activity_service.py` - Wraps DB queries for due activities.
*   `src/services/excel_importer.py` - Robust module for importing sheets into generic modules or activities.
*   `src/services/reminder_service.py` - Orchestrates the sending of tests and daily jobs.
*   `src/services/settings_service.py` - Resolves settings between DB overrides and `.env`.
*   `src/utils/helpers.py` - Text parsing and date checking tools.
*   `src/utils/logger.py` - Custom logger with console and file handlers.
*   `src/web/app.py` - The entire FastAPI application with routing, middleware, and rendering.
*   `src/whatsapp/whatsapp_sender.py` - HTTP request dispatching to Facebook Graph API.
*   `tests/*` (e.g., `test_email_template.py`, `test_schedule_checker.py`) - Basic unit tests.

### Partially Implemented
*   *None specifically*. All included files serve a complete, albeit sometimes basic, function.

### Skeleton / TODO
*   *None*. There are no placeholder files in the codebase.

### Dead Code
*   `src/excel/excel_reader.py`: The `ExcelActivityReader` class is largely bypassed in the new web-driven workflow in favor of `src/services/excel_importer.py`, which is more integrated with the SQLite DB. However, it may still be utilized by legacy components not fully deprecated.
*   `src/main.py`: Currently only delegates to `src.jobs.send_daily_reminders.run()`, acting as a backwards-compatibility alias.

### Potential Bugs
*   **`src/web/app.py`**: No pagination on routes returning rows (e.g., `/activities`, `/modules`), leading to scaling issues on massive datasets.
*   **`src/email/email_sender.py`**: Timeout logic is static; retries on failure are not implemented.
*   **`src/utils/logger.py`**: Uses `FileHandler` instead of `RotatingFileHandler`. Over time, `email.log` and `error.log` will grow indefinitely.
*   **`src/services/excel_importer.py`**: Loading entire workbooks in memory via `openpyxl` `data_only=True` might cause memory exhaustion on huge `.xlsx` files.
