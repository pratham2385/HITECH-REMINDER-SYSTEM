# Architecture & Security Audit Report
**Date:** July 2026
**Scope:** Full Repository Audit

This document outlines the findings of a comprehensive architectural and security audit of the HITECH Email Reminder System. The goal is to highlight vulnerabilities, bottlenecks, and anti-patterns, providing actionable recommendations without requiring a complete rewrite.

---

## 1. Security Issues

> [!CAUTION]
> **CSRF Vulnerability in Web Dashboard**
> The application uses a custom Cookie-based session (`activity_dashboard_session`) for authentication but lacks Cross-Site Request Forgery (CSRF) tokens. State-changing `POST` routes (e.g., `/settings/email`, `/users/new`) are vulnerable. A malicious site could force an authenticated administrator's browser to execute unwanted actions.
> **Fix:** Implement CSRF tokens in Jinja2 templates and validate them in a FastAPI dependency for all `POST` endpoints.

> [!WARNING]
> **Dangerous Hardcoded Defaults**
> In `src/config/settings.py`, if the `.env` file is missing or misconfigured, the system falls back to `local-dashboard-change-me` for the JWT secret key and `ChangeMe@123` for the Admin password. In production, this can lead to catastrophic unauthorized access.
> **Fix:** Raise an explicit `ValueError` if `SECRET_KEY` or `DASHBOARD_ADMIN_PASSWORD` are missing in production environments rather than defaulting to known strings.

> [!WARNING]
> **No Rate Limiting or Account Lockout**
> The `/login` endpoint has no protection against brute-force attacks.
> **Fix:** Add a simple memory-based rate limiter (e.g., `slowapi`) to throttle failed login attempts.

---

## 2. Bugs & Edge Cases

*   **Duplicate Startup Hooks:** In `src/web/app.py`, there are two `@app.on_event("startup")` decorators. Both attempt to initialize the database (`init_database()`). This is redundant and could cause unexpected overwrites or race conditions during application boot.
    *   **Fix:** Merge both startup functions into a single lifecycle event.
*   **Flawed Retry Logic:** In `src/services/reminder_service.py`, `retry_failed_notifications()` only checks if `email_status == "sent"`. If the email succeeds but the WhatsApp notification fails, the system considers the entire run successful and will *never* retry the WhatsApp message.
    *   **Fix:** Update the query to explicitly check for `whatsapp_status == 'failed'` independently of the email status.

---

## 3. Scalability & Database Issues

> [!IMPORTANT]
> **SQLite Concurrency Bottlenecks**
> The system now employs background polling (every 5 mins), retry jobs, and daily dispatches alongside web traffic. SQLite locks the entire database during writes. During a large Excel auto-import, web users will likely encounter `database is locked` timeouts.
> **Fix:** Migrate to PostgreSQL for production, or at minimum, enable SQLite WAL mode (`PRAGMA journal_mode=WAL;`) in the SQLAlchemy engine configuration.

*   **Hard Deletions on Import:** In `src/services/excel_importer.py`, re-importing a sheet triggers a hard `delete()` on all existing `ModuleField` and `ModuleDataRecord` rows. For tens of thousands of rows, this synchronous operation is extremely slow and bloats the database transaction log.
    *   **Fix:** Use an `upsert` mechanism (checking existing rows and updating them) or soft-deletions instead of blanket hard deletes.

---

## 4. Race Conditions & Scheduling Problems

*   **Multi-Worker Concurrency Catastrophe:** `APScheduler` is instantiated directly inside the FastAPI `app.py` startup event. If the application is deployed with multiple Uvicorn workers (e.g., `uvicorn app:app --workers 4`), **four independent schedulers will spawn**. At 8:00 AM, the system will send the daily reminder 4 times to every recipient.
    *   **Fix:** Decouple the scheduler from the web API. Run the scheduler as a separate standalone Python process (`python scripts/run_scheduler.py`), OR use a distributed lock (e.g., Redis) to ensure only one worker executes the job.

*   **Global Variable State:** `last_mtime` in `background_tasks.py` is a module-level global variable. In a multi-worker setup, this state is not shared, causing redundant overlapping file imports.

---

## 5. Architectural Anti-Patterns (Bad Architecture)

*   **Naming Collisions:** The repository contains `src/models.py` (Domain Dataclasses) and `src/db/models.py` (SQLAlchemy Entities). While separating persistence from domain logic is a great pattern, naming both `models.py` causes severe cognitive overhead and high risk of import shadowing.
    *   **Fix:** Rename `src/models.py` to `src/domain.py` or `src/schemas.py`.
*   **Engine Thrashing:** `get_session_factory(settings)` is called repeatedly inside `background_tasks.py` jobs. This creates a brand new SQLAlchemy Engine on every background tick rather than utilizing a shared connection pool.
    *   **Fix:** Instantiate the engine once globally (or inject it) and reuse it across the application lifecycle.
*   **Blocking Async Event Loop:** The background jobs perform blocking I/O (SMTP network calls, Database writes) inside standard synchronous functions.
    *   **Fix:** Use `AsyncIOScheduler` and `httpx`/`aiosmtplib` to prevent blocking the main event loop, or offload heavy tasks to background threads via `run_in_threadpool`.

---

## 6. Duplicate Logic

*   **Test Dispatch Duplication:** `send_test_email` and `send_test_whatsapp` in `src/services/reminder_service.py` heavily duplicate the logging and templating logic found in `send_daily_reminders`.
    *   **Fix:** Abstract the core dispatch mechanism into a private `_dispatch_notification()` method that takes the content and channel as arguments.
