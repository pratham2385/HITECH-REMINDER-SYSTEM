# HITECH Email Reminder System

A robust, full-stack compliance reminder and notification system built for medical/legal environments. It syncs with Excel workbooks and dispatches automated Email and WhatsApp notifications on customizable schedules.

## Core Features

- **Excel Sync**: Automatically imports and syncs compliance activities from Excel `.xlsx` files via manual upload or background file monitoring.
- **Smart Scheduler**: Supports Daily, Weekly, Bi-weekly, Monthly, Quarterly, and Yearly frequencies with edge-case handling (e.g. End-of-month overflows).
- **Multi-Channel Dispatch**: Distributes HTML-formatted summary emails and Meta Business Cloud WhatsApp templates to multiple configured recipients.
- **Background Execution**: Built-in APScheduler manages daily dispatches, file monitoring, and automatic hourly retries for failed notifications.
- **Interactive Dashboard**: A FastAPI + Jinja2 web interface for user management, settings configuration, and historical auditing.

## Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5 / CSS3 / Jinja2 (No JS frameworks required)
- **Background Jobs**: APScheduler

## Quickstart

### Prerequisites
- Python 3.11+
- Virtual environment

### Installation

1. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
2. Create and activate a virtual environment, then install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Initialize the database schema:
   ```bash
   python migrate.py
   ```
4. Run the development server:
   ```bash
   uvicorn src.web.app:app --reload
   ```

## Production Deployment
Please refer to `DEPLOYMENT.md` for instructions on running via Docker Compose or Windows Task Scheduler.

## License
Proprietary / Closed Source.
