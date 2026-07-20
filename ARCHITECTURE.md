# Architecture Overview: HITECH Email Reminder System

The HITECH Email Reminder System is a monolithic Python application combining scheduled CLI tasks and a web-based management dashboard.

## Folder Structure
```text
email-reminder-system/
|-- data/                 # Data directory (Excel source of truth, SQLite DB)
|-- logs/                 # System and error logs
|-- src/
|   |-- config/           # Environment configurations and DB settings mapping
|   |-- db/               # SQLAlchemy ORM definitions and SQLite session management
|   |-- email/            # SMTP wrapper and template builder
|   |-- excel/            # Legacy basic pandas Excel reader
|   |-- jobs/             # Entrypoints (CLI scripts) for specific tasks
|   |-- scheduler/        # Core business logic for interpreting Date/Frequency strings
|   |-- services/         # Orchestration layer (business logic connecting DB, Mail, Excel)
|   |-- utils/            # Helper functions and Logger setup
|   |-- web/              # FastAPI application, HTML templates, CSS
|   |-- whatsapp/         # Meta Graph API wrapper for WhatsApp
|-- tests/                # Unit tests
```

## Services
*   **ActivityService**: Converts ORM records to domain models; fetches activities due on a specific date or upcoming within X days.
*   **ExcelImporter**: Analyzes Excel workbook sheets, detects generic modules vs. activity lists, and imports rows as dynamic JSON `ModuleDataRecord` or structured `ActivityRecord`.
*   **ReminderService**: Orchestrates the daily reminder routine. It fetches due activities, constructs the email and WhatsApp payloads, dispatches them, and logs success/failures back into the database.
*   **SettingsService**: Overrides `.env` configurations with values updated via the web dashboard.

## Scheduler Flow
1.  The scheduler retrieves a list of active `ActivityRecord` entries from the database.
2.  `ScheduleChecker` analyzes the `Frequency` and `Date` fields against the target execution date.
    *   **Daily**: Always returns True.
    *   **Monthly**: Matches the day of the month or evaluates "last day of month" logic.
    *   **Quarterly**: Matches if the execution month is Jan, Apr, Jul, Oct, and the day matches.
    *   **Yearly**: Matches if the execution month matches the parsed textual or numeric month representation.
3.  Matching activities are bundled into a dispatch list.

## Database Schema (SQLite & SQLAlchemy)
*   `users`: Authentication details (Username, PBKDF2 hash, role).
*   `activities`: The core reminder entities (Activity name, Frequency, Date, Status, Link, Remark).
*   `modules` / `module_fields` / `module_records`: Generic EAV/JSON tables to store non-activity sheets imported from Excel.
*   `workbook_imports` / `imported_sheets`: Audit trails for Excel files uploaded to the dashboard.
*   `reminder_runs` / `email_logs` / `whatsapp_logs`: Audit logs detailing when jobs ran and message delivery status.
*   `notification_settings`: Key-value store for application config, capable of overriding environment variables securely.

## Workflows

### Reminder Workflow
1.  Triggered externally (e.g., Windows Task Scheduler) by executing `python -m src.jobs.send_daily_reminders`.
2.  Loads settings (merging `.env` and DB overrides).
3.  Queries `ActivityService` for activities due today.
4.  If matches exist, compiles the payload via `EmailTemplate`.
5.  Dispatches email via `GmailEmailSender` and WhatsApp message via `WhatsAppSender`.
6.  Records the execution and delivery outcome in `ReminderRun`, `EmailLog`, and `WhatsAppLog`.

### Excel Import Workflow
1.  User uploads a `.xlsx` file via the Dashboard (`/imports/new`) or CLI.
2.  `ExcelImportService` analyzes the file and generates a preview.
3.  Upon confirmation, the service iterates through sheets.
    *   Generic sheets are mapped to a new `Module`, with headers acting as `ModuleField` and rows as `ModuleDataRecord` (JSON).
    *   Sheets containing `Activity`, `Frequency`, and `Date` columns automatically populate the `activities` table.
4.  Logs the operation in `WorkbookImport` and `ImportedSheet`.

### Dashboard Workflow
1.  A FastAPI instance running on Uvicorn serves web traffic.
2.  Users authenticate via the `/login` route, receiving a signed HMAC cookie.
3.  Authenticated users (Roles: owner, staff, viewer) access Jinja2-rendered HTML views.
4.  The dashboard provides CRUD operations for users, activities, modules, and allows triggering test emails/WhatsApp messages directly.

### WhatsApp Workflow
1.  Evaluates if WhatsApp is enabled in DB settings.
2.  Requires a Meta Developer App configured with the WhatsApp Business Cloud API.
3.  Constructs a JSON payload referencing a pre-approved Meta Template (`whatsapp_template_name`).
4.  Fires an HTTP POST request to `graph.facebook.com` using the provided token.
5.  Extracts the `provider_message_id` for success logging.

### Authentication System
1.  Custom-built, avoiding heavy external auth libraries.
2.  Passwords hashed using `pbkdf2_hmac` (SHA-256 with 200,000 iterations) and salted randomly.
3.  On login success, generates a payload containing `user_id` and `expires_at`.
4.  The payload is signed using `hmac.new` with a `SECRET_KEY` and appended as a signature.
5.  Stored in the client browser as an HTTP-only cookie (`activity_dashboard_session`). Middleware parses and verifies the signature on subsequent requests to inject the `User` context.
