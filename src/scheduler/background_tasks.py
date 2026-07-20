"""Background scheduling for FastAPI application."""

from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from src.config.settings import load_settings
from src.db.session import get_session_factory
from src.services.reminder_service import send_daily_reminders

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def dispatch_reminders_job() -> None:
    """Job to run the daily reminder dispatch."""
    settings = load_settings()
    SessionLocal = get_session_factory(settings.database_url)
    db: Session = SessionLocal()
    try:
        logger.info("Starting background daily reminder dispatch.")
        result = send_daily_reminders(db, settings, logger)
        db.commit()
        logger.info("Background daily reminder dispatch completed: %s", result.message)
    except Exception as exc:
        logger.error("Error in background daily reminder dispatch: %s", exc)
        db.rollback()
    finally:
        db.close()


def retry_failed_notifications_job() -> None:
    """Job to retry failed notifications from the last 24 hours."""
    from src.services.reminder_service import retry_failed_notifications
    settings = load_settings()
    SessionLocal = get_session_factory(settings.database_url)
    db: Session = SessionLocal()
    try:
        logger.info("Starting background retry for failed notifications.")
        retry_failed_notifications(db, settings, logger)
        db.commit()
        logger.info("Background retry completed.")
    except Exception as exc:
        logger.error("Error in background retry dispatch: %s", exc)
        db.rollback()
    finally:
        db.close()


last_mtime = 0.0

def poll_excel_changes_job() -> None:
    """Check if the Excel file has been modified and auto-import it."""
    global last_mtime
    import os
    import glob
    from src.services.excel_importer import ExcelImportService
    
    settings = load_settings()
    
    data_dir = str(settings.data_dir) if hasattr(settings, 'data_dir') else "data"
    excel_files = glob.glob(os.path.join(data_dir, "*.xlsx"))
    if not excel_files:
        return
    
    latest_file = max(excel_files, key=os.path.getmtime)
    current_mtime = os.path.getmtime(latest_file)
    
    if last_mtime == 0.0:
        last_mtime = current_mtime
        return
        
    if current_mtime > last_mtime:
        logger.info("Detected changes in %s. Auto-importing...", latest_file)
        SessionLocal = get_session_factory(settings.database_url)
        db: Session = SessionLocal()
        try:
            with open(latest_file, "rb") as f:
                content = f.read()
            filename = os.path.basename(latest_file)
            importer = ExcelImportService(db, logger)
            result = importer.import_workbook(filename, content)
            db.commit()
            logger.info("Auto-import completed: %s", result.message)
            last_mtime = current_mtime
        except Exception as exc:
            logger.error("Error during auto-import: %s", exc)
            db.rollback()
        finally:
            db.close()


def start_scheduler() -> None:
    """Start the background scheduler for automatic jobs."""
    if scheduler.running:
        return
        
    # Schedule the daily reminder dispatch to run at 8:00 AM every day
    scheduler.add_job(
        dispatch_reminders_job,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_reminders",
        replace_existing=True,
    )
    
    # Schedule retries every hour
    scheduler.add_job(
        retry_failed_notifications_job,
        trigger=CronTrigger(minute=0),
        id="hourly_retries",
        replace_existing=True,
    )
    
    # Schedule Excel file polling every 5 minutes
    from apscheduler.triggers.interval import IntervalTrigger
    scheduler.add_job(
        poll_excel_changes_job,
        trigger=IntervalTrigger(minutes=5),
        id="excel_auto_import",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started successfully.")

