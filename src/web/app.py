"""Responsive dashboard web application."""

from __future__ import annotations

import json
import typing
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.config.settings import APP_NAME, STATIC_DIR, TEMPLATE_DIR, load_settings
from src.db.models import (
    ActivityRecord,
    EmailLog,
    Module,
    ModuleDataRecord,
    ModuleField,
    ReminderRun,
    User,
    WorkbookImport,
    TaskCollection,
    Recipient,
)
from src.db.session import get_session_factory, init_database
from src.security import hash_password, sign_session, verify_password, verify_session
from src.services.activity_service import (
    activity_record_to_domain,
    get_due_activity_records,
    get_upcoming_activity_records,
)
from src.services.excel_importer import ExcelImportService
from src.services.reminder_service import (
    build_preview_content,
    get_due_domain_activities,
    send_test_email,
)
from src.services.settings_service import effective_settings, masked, set_setting
from src.utils.logger import setup_logging


settings = load_settings()
logger = setup_logging(settings.log_dir)
app = FastAPI(title=APP_NAME)

FREQUENCIES = ["Daily", "Monthly", "Quarterly", "Yearly"]
ROLES = ["owner", "staff", "viewer"]

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.on_event("startup")
def startup_event() -> None:
    """Initialize database and background scheduler on application startup."""
    init_database(settings)
    try:
        from src.scheduler.background_tasks import start_scheduler
        start_scheduler()
    except ImportError as e:
        logger.error(f"Failed to start scheduler: {e}")

# Templates and helpers imported from app_deps
from src.web.app_deps import (
    redirect, current_user, user_context, render, require_login, 
    require_admin, require_manager, require_editor, redirect_with_msg,
    get_db, close_db, SESSION_COOKIE, templates
)
from src.web.auth_routes import router as auth_router
from src.web.csrf import generate_csrf_token, verify_csrf_token

app.include_router(auth_router)

def parse_json_values(record) -> dict[str, object]:
    """Parse a module row JSON payload."""
    try:
        values = json.loads(record.values_json)
    except json.JSONDecodeError:
        return {}
    return values if isinstance(values, dict) else {}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Return an empty response for favicon.ico to prevent 404 errors in logs."""
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> RedirectResponse:
    """Redirect to workspaces or login."""
    db = get_db()
    try:
        user = current_user(request, db)
        return redirect("/collections" if user else "/login")
    finally:
        close_db(db)


@app.get("/workspaces", response_class=HTMLResponse)
def workspaces(request: Request) -> RedirectResponse:
    """Alias redirect to workspaces collection page."""
    return redirect("/collections")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user

        today = date.today()
        due_records = get_due_activity_records(db, logger)
        upcoming = get_upcoming_activity_records(db, today, logger, days=30, limit=12)
        active_workspace = db.query(TaskCollection).filter_by(is_active=True).first()
        activities_query = db.query(ActivityRecord).filter(ActivityRecord.is_active.is_(True))
        if active_workspace:
            activities_query = activities_query.filter(ActivityRecord.collection_id == active_workspace.id)
            
        activities = activities_query.all()
        categories = sorted(list(set(a.category for a in activities if a.category)))
        
        pending_count = sum(1 for row in activities if (row.status or "").strip().casefold() != "done")
        done_count = sum(1 for row in activities if (row.status or "").strip().casefold() == "done")
        last_run = db.query(ReminderRun).order_by(ReminderRun.created_at.desc()).first()
        last_email = db.query(EmailLog).order_by(EmailLog.created_at.desc()).first()
        modules = categories[:8]
        module_count = len(categories)
        
        from datetime import datetime
        first_day_of_month = datetime(today.year, today.month, 1)
        
        user_count = db.query(Recipient.email).join(TaskCollection, Recipient.workspace_id == TaskCollection.id).filter(TaskCollection.is_active == True).distinct().count()
        emails_sent_mtd = db.query(EmailLog).filter(EmailLog.created_at >= first_day_of_month).count()
        failed_emails = db.query(EmailLog).filter(EmailLog.success == False).count()
        
        # Real-time Email Logs
        recent_emails = db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(10).all()
        
        # Monthly data
        from sqlalchemy import func, extract
        six_months_ago = datetime(today.year, today.month, 1)
        for _ in range(5):
            if six_months_ago.month == 1:
                six_months_ago = six_months_ago.replace(year=six_months_ago.year - 1, month=12)
            else:
                six_months_ago = six_months_ago.replace(month=six_months_ago.month - 1)
                
        monthly_stats = db.query(
            extract('year', EmailLog.created_at).label('year'),
            extract('month', EmailLog.created_at).label('month'),
            func.count(EmailLog.id).label('count')
        ).filter(EmailLog.created_at >= six_months_ago).group_by('year', 'month').all()
        
        # Success vs Failure
        total_emails_all_time = db.query(EmailLog).count()
        total_failed_all_time = failed_emails
        total_success_all_time = total_emails_all_time - total_failed_all_time
        
        # Initialize default lists for the last 6 months
        months_labels = []
        months_data = []
        current = six_months_ago
        for _ in range(6):
            months_labels.append(current.strftime('%b'))
            # find match
            match = next((s for s in monthly_stats if s.year == current.year and s.month == current.month), None)
            months_data.append(match.count if match else 0)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return render(
            request,
            "dashboard.html",
            {
                "today": today,
                "due_records": due_records,
                "upcoming": upcoming,
                "pending_count": pending_count,
                "done_count": done_count,
                "activity_count": len(activities),
                "module_count": module_count,
                "last_run": last_run,
                "last_email": last_email,
                "modules": modules,
                "user_count": user_count,
                "emails_sent_mtd": emails_sent_mtd,
                "failed_emails": failed_emails,
                "recent_emails": recent_emails,
                "chart_months_labels": json.dumps(months_labels),
                "chart_months_data": json.dumps(months_data),
                "chart_success_data": json.dumps([total_success_all_time, total_failed_all_time]),
            },
            user,
        )
    finally:
        close_db(db)

@app.post("/dashboard/clear_recent_activity")
def dashboard_clear_recent_activity(request: Request, csrf_token: str = Form(...)) -> typing.Any:
    print(f"dashboard_clear_recent_activity called! CSRF: {csrf_token[:10]}...")
    if not verify_csrf_token(request, csrf_token):
        print("CSRF verification failed!")
        return HTMLResponse(status_code=403)
        
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            print("User not logged in!")
            return user
        
        if user.role not in {"admin", "manager", "owner", "staff"}:
            print("User cannot edit!")
            return HTMLResponse(status_code=403)
            
        count = db.query(EmailLog).delete()
        db.commit()
        print(f"Deleted {count} email logs!")
        
        return HTMLResponse(status_code=200, headers={"HX-Refresh": "true"})
    finally:
        close_db(db)

@app.get("/dashboard/monitor", response_class=HTMLResponse)
def dashboard_monitor(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return HTMLResponse(status_code=401)

        today = date.today()
        from datetime import datetime
        start_of_today = datetime(today.year, today.month, today.day)
        
        # Activity Stats
        active_workspace = db.query(TaskCollection).filter_by(is_active=True).first()
        activities_query = db.query(ActivityRecord).filter(ActivityRecord.is_active.is_(True))
        if active_workspace:
            activities_query = activities_query.filter(ActivityRecord.collection_id == active_workspace.id)
            
        activities = activities_query.all()
        pending_count = sum(1 for row in activities if (row.status or "").strip().casefold() != "done")
        done_count = sum(1 for row in activities if (row.status or "").strip().casefold() == "done")
        activity_count = len(activities)
        
        # Email Stats Today
        emails_sent_today = db.query(EmailLog).filter(EmailLog.created_at >= start_of_today).count()
        failed_emails_today = db.query(EmailLog).filter(EmailLog.created_at >= start_of_today, EmailLog.success == False).count()
        recent_emails = db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(10).all()
        
        # Scheduler Status
        last_run = db.query(ReminderRun).order_by(ReminderRun.created_at.desc()).first()
        scheduler_active = False
        if last_run:
            # If the scheduler ran within the last hour, consider it active
            if (datetime.utcnow() - last_run.created_at).total_seconds() < 3600:
                scheduler_active = True
            
        upcoming = get_upcoming_activity_records(db, today, logger, days=30, limit=12)
        
        # Totals
        user_count = db.query(Recipient.email).join(TaskCollection, Recipient.workspace_id == TaskCollection.id).filter(TaskCollection.is_active == True).distinct().count()
        module_count = db.query(Module).count()

        return render(
            request,
            "dashboard_monitor.html",
            {
                "today": today,
                "activity_count": activity_count,
                "pending_count": pending_count,
                "done_count": done_count,
                "emails_sent_today": emails_sent_today,
                "failed_emails_today": failed_emails_today,
                "recent_emails": recent_emails,
                "scheduler_active": scheduler_active,
                "last_run": last_run,
                "upcoming": upcoming,
                "user_count": user_count,
                "module_count": module_count,
                "csrf_token": generate_csrf_token(request),
            },
            user,
        )
    finally:
        close_db(db)


@app.get("/activities", response_class=HTMLResponse)
def activities(
    request: Request,
    search: str = "",
    recipient_id: str = "",
    module_id: str = ""
) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
            
        active_collection = db.query(TaskCollection).filter(TaskCollection.is_active == True).first()
        query = db.query(ActivityRecord).filter(ActivityRecord.is_active.is_(True))
        
        if active_collection:
            query = query.filter(ActivityRecord.collection_id == active_collection.id)

        if search:
            query = query.filter(ActivityRecord.activity.ilike(f"%{search}%"))
            
        if recipient_id and recipient_id != "all":
            try:
                rid = int(recipient_id)
                query = query.filter(ActivityRecord.recipient_id == rid)
            except ValueError:
                pass
                
        if module_id and module_id != "all":
            query = query.filter(ActivityRecord.category == module_id)
                
        rows = query.order_by(ActivityRecord.sort_order.asc(), ActivityRecord.id.asc()).all()
        
        categories = sorted(list(set(a.category for a in rows if a.category)))
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.display_name.asc()).all()
        recipients = []
        if active_collection:
            recipients = db.query(Recipient).filter(Recipient.workspace_id == active_collection.id).all()
        else:
            recipients = db.query(Recipient).all()
        
        return render(
            request, 
            "activities.html", 
            {
                "activities": rows,
                "categories": categories,
                "users": users,
                "recipients": recipients,
                "search": search,
                "recipient_id": recipient_id,
                "module_id": module_id,
                "active_collection": active_collection
            }, 
            user
        )
    finally:
        close_db(db)


@app.get("/activities/new", response_class=HTMLResponse)
def activity_new(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.display_name.asc()).all()
        active_collection = db.query(TaskCollection).filter(TaskCollection.is_active == True).first()
        recipients = db.query(Recipient).filter(Recipient.workspace_id == active_collection.id).all() if active_collection else db.query(Recipient).all()
        categories = sorted(list(set(a.category for a in db.query(ActivityRecord).all() if a.category)))
        return render(
            request,
            "activity_form.html",
            {"activity": None, "categories": categories, "users": users, "recipients": recipients, "frequencies": FREQUENCIES},
            user,
        )
    finally:
        close_db(db)


@app.post("/activities/new")
def activity_create(
    request: Request,
    activity: str = Form(...),
    frequency: str = Form(...),
    date_value: str = Form(""),
    link: str = Form(""),
    status: str = Form(""),
    remark: str = Form(""),
    category: str = Form(""),
    recipient_id: str = Form(""),
    assigned_user_id: str = Form(""),
    timezone: str = Form("UTC"),
    send_time: str = Form("09:00"),
    day_of_week: str = Form(""),
    day_of_month: str = Form(""),
    month_of_year: str = Form(""),
    year: str = Form(""),
    quarter_months: typing.List[str] = Form(default=[]),
    date_handling_strategy: str = Form("exact"),
    email_subject_template: str = Form(""),
    email_body_template: str = Form(""),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        sort_order = db.query(ActivityRecord).count() + 1
        from src.scheduler.scheduler_engine import get_next_run_time
        from datetime import datetime
        now = datetime.utcnow()
        
        day_of_month_int = int(day_of_month) if day_of_month else None
        month_of_year_int = int(month_of_year) if month_of_year else None
        year_int = int(year) if year else None
        quarter_months_str = ",".join(quarter_months) if quarter_months else None
        
        # Strict Calendar Validation
        if day_of_month_int and month_of_year_int and year_int:
            from datetime import date
            try:
                # This will raise ValueError for e.g. 31 April or 29 Feb 2027
                validated_date = date(year_int, month_of_year_int, day_of_month_int)
                computed_day = validated_date.strftime("%A")
                
                if day_of_week and day_of_week.strip().lower() != computed_day.lower():
                    # Return error if user selected wrong day
                    return redirect(f"/activities?error=Selected day ({day_of_week}) does not match the date ({validated_date.strftime('%d %B %Y')}, which is a {computed_day}).")
                
                # Auto-populate day of week if left empty
                day_of_week = computed_day
            except ValueError as e:
                return redirect(f"/activities?error=Invalid calendar date: {e}")
        
        next_run = get_next_run_time(
            frequency=frequency.strip(),
            timezone_str=timezone.strip(),
            send_time_str=send_time.strip(),
            day_of_week=day_of_week.strip() if day_of_week else None,
            day_of_month=day_of_month_int,
            month_of_year=month_of_year_int,
            year=year_int,
            quarter_months=quarter_months_str,
            date_handling_strategy=date_handling_strategy.strip(),
            from_time_utc=now
        )
        
        db.add(
            ActivityRecord(
                activity=activity.strip(),
                frequency=frequency.strip(),
                date_value=date_value.strip(),
                link=link.strip(),
                status=status.strip(),
                remark=remark.strip(),
                category=category.strip() if category else None,
                recipient_id=int(recipient_id) if recipient_id else None,
                assigned_user_id=int(assigned_user_id) if assigned_user_id else None,
                timezone=timezone.strip(),
                send_time=send_time.strip(),
                day_of_week=day_of_week.strip() if day_of_week else None,
                day_of_month=day_of_month_int,
                month_of_year=month_of_year_int,
                year=year_int,
                quarter_months=quarter_months_str,
                date_handling_strategy=date_handling_strategy.strip(),
                email_subject_template=email_subject_template.strip() if email_subject_template else None,
                email_body_template=email_body_template.strip() if email_body_template else None,
                next_run_at=next_run,
                sort_order=sort_order,
                is_active=True,
            )
        )
        db.commit()
        return redirect("/activities?notice=Activity created")
    finally:
        close_db(db)


@app.get("/activities/{activity_id}/edit", response_class=HTMLResponse)
def activity_edit(request: Request, activity_id: int) -> typing.Any:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        activity = db.query(ActivityRecord).filter(ActivityRecord.id == activity_id).first()
        if activity is None:
            return redirect("/activities?error=Activity not found")
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.display_name.asc()).all()
        active_collection = db.query(TaskCollection).filter(TaskCollection.is_active == True).first()
        recipients = db.query(Recipient).filter(Recipient.workspace_id == active_collection.id).all() if active_collection else db.query(Recipient).all()
        categories = sorted(list(set(a.category for a in db.query(ActivityRecord).all() if a.category)))
        return render(
            request,
            "activity_form.html",
            {"activity": activity, "categories": categories, "users": users, "recipients": recipients, "frequencies": FREQUENCIES},
            user,
        )
    finally:
        close_db(db)


@app.post("/activities/{activity_id}/edit")
def activity_update(
    request: Request,
    activity_id: int,
    activity: str = Form(...),
    frequency: str = Form(...),
    date_value: str = Form(""),
    link: str = Form(""),
    status: str = Form(""),
    remark: str = Form(""),
    category: str = Form(""),
    recipient_id: str = Form(""),
    assigned_user_id: str = Form(""),
    timezone: str = Form("UTC"),
    send_time: str = Form("09:00"),
    day_of_week: str = Form(""),
    day_of_month: str = Form(""),
    month_of_year: str = Form(""),
    year: str = Form(""),
    quarter_months: typing.List[str] = Form(default=[]),
    date_handling_strategy: str = Form("exact"),
    email_subject_template: str = Form(""),
    email_body_template: str = Form(""),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        row = db.query(ActivityRecord).filter(ActivityRecord.id == activity_id).first()
        if row is None:
            return redirect("/activities?error=Activity not found")
        row.activity = activity.strip()
        row.frequency = frequency.strip()
        row.date_value = date_value.strip()
        row.link = link.strip()
        row.status = status.strip()
        row.remark = remark.strip()
        row.category = category.strip() if category else None
        row.recipient_id = int(recipient_id) if recipient_id else None
        row.assigned_user_id = int(assigned_user_id) if assigned_user_id else None
        
        day_of_month_int = int(day_of_month) if day_of_month else None
        month_of_year_int = int(month_of_year) if month_of_year else None
        year_int = int(year) if year else None
        quarter_months_str = ",".join(quarter_months) if quarter_months else None
        
        # Strict Calendar Validation
        if day_of_month_int and month_of_year_int and year_int:
            from datetime import date
            try:
                # This will raise ValueError for e.g. 31 April or 29 Feb 2027
                validated_date = date(year_int, month_of_year_int, day_of_month_int)
                computed_day = validated_date.strftime("%A")
                
                if day_of_week and day_of_week.strip().lower() != computed_day.lower():
                    # Return error if user selected wrong day
                    return redirect(f"/activities?error=Selected day ({day_of_week}) does not match the date ({validated_date.strftime('%d %B %Y')}, which is a {computed_day}).")
                
                # Auto-populate day of week if left empty
                day_of_week = computed_day
            except ValueError as e:
                return redirect(f"/activities?error=Invalid calendar date: {e}")
                
        row.timezone = timezone.strip()
        row.send_time = send_time.strip()
        row.day_of_week = day_of_week.strip() if day_of_week else None
        row.day_of_month = day_of_month_int
        row.month_of_year = month_of_year_int
        row.year = year_int
        row.quarter_months = quarter_months_str
        row.date_handling_strategy = date_handling_strategy.strip()
        row.email_subject_template = email_subject_template.strip() if email_subject_template else None
        row.email_body_template = email_body_template.strip() if email_body_template else None
        
        from src.scheduler.scheduler_engine import get_next_run_time
        from datetime import datetime
        now = datetime.utcnow()
        row.next_run_at = get_next_run_time(
            frequency=row.frequency,
            timezone_str=row.timezone,
            send_time_str=row.send_time,
            day_of_week=row.day_of_week,
            day_of_month=row.day_of_month,
            month_of_year=row.month_of_year,
            year=row.year,
            quarter_months=row.quarter_months,
            date_handling_strategy=row.date_handling_strategy,
            from_time_utc=now
        )
        
        db.commit()
        return redirect("/activities?notice=Activity updated")
    finally:
        close_db(db)


@app.post("/activities/{activity_id}/delete")
def activity_delete(request: Request, activity_id: int) -> typing.Any:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        row = db.query(ActivityRecord).filter(ActivityRecord.id == activity_id).first()
        if row:
            row.is_active = False
            db.commit()
            
        if request.headers.get("HX-Request"):
            response = HTMLResponse(content="")
            response.headers["HX-Trigger"] = "activityDeleted"
            return response
            
        return redirect("/activities?notice=Activity deleted")
    finally:
        close_db(db)


@app.post("/activities/{activity_id}/send-reminder")
def activity_send_reminder(request: Request, activity_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
            
        activity = db.query(ActivityRecord).filter(ActivityRecord.id == activity_id).first()
        if not activity:
            return redirect("/activities?error=Activity not found")
            
        from src.services.reminder_service import send_daily_reminders
        from src.services.activity_service import activity_record_to_domain
        from src.email.email_template import EmailTemplate
        from src.email.email_sender import GmailEmailSender
        from src.services.settings_service import effective_settings
        
        active_settings = effective_settings(db, settings)
        domain_act = activity_record_to_domain(activity)
        
        target_email = domain_act.assigned_user_email or active_settings.recipient_email.split(",")[0]
        if not target_email:
            return redirect("/activities?error=No target email configured.")
            
        email_content = EmailTemplate.build(target_email, [domain_act], date.today())
        
        # Override the subject for manual reminders to prevent Gmail thread collapsing
        # and to make it clear which activity this is for.
        import time
        custom_subject = f"Manual Reminder: {domain_act.activity} ({int(time.time())})"
        from src.models import EmailContent
        custom_content = EmailContent(
            recipient=email_content.recipient,
            subject=custom_subject,
            body=email_content.body
        )
        
        email_result = GmailEmailSender(active_settings, logger).send(custom_content)
        
        if email_result.success:
            return redirect("/activities?notice=Reminder sent successfully!")
        else:
            return redirect(f"/activities?error=Failed to send: {email_result.message}")
            
    finally:
        close_db(db)


@app.get("/imports", response_class=HTMLResponse)
def imports(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        rows = db.query(WorkbookImport).order_by(WorkbookImport.created_at.desc()).all()
        return render(request, "imports.html", {"imports": rows}, user)
    finally:
        close_db(db)


@app.get("/imports/new", response_class=HTMLResponse)
def import_new(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        return render(request, "import_new.html", {}, user)
    finally:
        close_db(db)


@app.post("/imports/new")
async def import_upload(request: Request, workbook: UploadFile = File(...)) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        if not workbook.filename or not workbook.filename.lower().endswith(".xlsx"):
            return redirect("/imports/new?error=Please upload an .xlsx file")

        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(workbook.filename).name
        stored_path = settings.upload_dir / f"{uuid4().hex}_{safe_name}"
        stored_path.write_bytes(await workbook.read())

        importer = ExcelImportService(settings.upload_dir)
        pending = importer.create_pending_import(db, safe_name, stored_path, user.id)
        db.commit()
        return redirect(f"/imports/{pending.id}")
    except Exception as exc:
        db.rollback()
        logger.exception("Excel upload failed")
        return redirect(f"/imports/new?error={str(exc)}")
    finally:
        close_db(db)


@app.get("/imports/{import_id}", response_class=HTMLResponse)
def import_detail(request: Request, import_id: int) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        record = db.query(WorkbookImport).filter(WorkbookImport.id == import_id).first()
        if record is None:
            return redirect("/imports?error=Import not found")
        preview = None
        if record.status == "pending":
            preview = ExcelImportService(settings.upload_dir).preview_workbook(Path(record.stored_path))
        return render(request, "import_detail.html", {"import_record": record, "preview": preview}, user)
    finally:
        close_db(db)

@app.post("/imports/{import_id}/delete")
def import_delete(request: Request, import_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        record = db.query(WorkbookImport).filter(WorkbookImport.id == import_id).first()
        if not record:
            return redirect("/imports?error=Import not found")
        
        # Optional: delete the file from the system
        if record.stored_path:
            import os
            try:
                if os.path.exists(record.stored_path):
                    os.remove(record.stored_path)
            except OSError:
                pass
                
        # Delete corresponding workspace if it exists
        workspace = db.query(TaskCollection).filter(
            TaskCollection.description == f"Auto-generated workspace for import {import_id}"
        ).first()
        if workspace:
            if workspace.is_active:
                return redirect("/imports?error=Cannot delete import because its workspace is active")
            db.delete(workspace)

        db.delete(record)
        db.commit()
        return redirect("/imports?notice=Import deleted successfully")
    finally:
        close_db(db)


@app.post("/imports/{import_id}/confirm")
def import_confirm(
    request: Request,
    import_id: int,
    import_activity_sheets: str = Form("yes"),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        record = db.query(WorkbookImport).filter(WorkbookImport.id == import_id).first()
        if record is None:
            return redirect("/imports?error=Import not found")
        if record.status != "pending":
            return redirect(f"/imports/{import_id}?error=Workbook was already imported")
        ExcelImportService(settings.upload_dir).import_workbook(
            db,
            record,
            import_activity_sheets=import_activity_sheets == "yes",
        )
        db.commit()
        return redirect(f"/imports/{import_id}?notice=Workbook imported")
    except Exception as exc:
        db.rollback()
        logger.exception("Excel import confirm failed")
        return redirect(f"/imports/{import_id}?error={str(exc)}")
    finally:
        close_db(db)


@app.get("/settings/email", response_class=HTMLResponse)
def email_settings(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        active = effective_settings(db, settings)
        return render(
            request,
            "settings_email.html",
            {"settings": active, "masked_password": masked(active.email_app_password)},
            user,
        )
    finally:
        close_db(db)


@app.post("/settings/email")
def email_settings_save(
    request: Request,
    email_address: str = Form(""),
    email_app_password: str = Form(""),
    recipient_email: str = Form(""),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        set_setting(db, "EMAIL_ADDRESS", email_address.strip())
        if email_app_password.strip():
            set_setting(db, "EMAIL_APP_PASSWORD", email_app_password.strip(), is_secret=True)
        set_setting(db, "RECIPIENT_EMAIL", recipient_email.strip())
        db.commit()
        return redirect("/settings/email?notice=Email settings saved")
    finally:
        close_db(db)





@app.get("/reminders/preview", response_class=HTMLResponse)
def reminders_preview(request: Request, preview_date: str = None) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        
        target_date = date.today()
        if preview_date:
            try:
                target_date = date.fromisoformat(preview_date)
            except ValueError:
                pass
                
        # We must pass the target_date to the service methods.
        # But wait, build_preview_content currently calls get_due_domain_activities(session, logger, run_date)
        # We need to make sure the service method is updated as well.
        # It's already in reminder_service.py as build_preview_content(session, logger, run_date)
        
        from src.services.reminder_service import get_due_domain_activities, build_preview_content
        due_activities = get_due_domain_activities(db, logger, target_date)
        content = build_preview_content(db, logger, target_date)
        return render(
            request,
            "reminders_preview.html",
            {"due_activities": due_activities, "content": content, "preview_date": target_date.isoformat()},
            user,
        )
    finally:
        close_db(db)


@app.post("/reminders/send-test-email")
def reminders_send_test_email(request: Request) -> RedirectResponse:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        result = send_test_email(db, settings, logger)
        db.commit()
        target = "notice" if result.success else "error"
        return redirect(f"/reminders/preview?{target}={result.message}")
    finally:
        close_db(db)





@app.get("/collections", response_class=HTMLResponse)
def collections_list(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        collections = db.query(TaskCollection).order_by(TaskCollection.created_at.desc()).all()
        return render(request, "collections.html", {"collections": collections}, user)
    finally:
        close_db(db)

@app.get("/collections/new", response_class=HTMLResponse)
def collections_new(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        return render(request, "collection_form.html", {"collection": None}, user)
    finally:
        close_db(db)

@app.post("/collections/new")
def collections_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user

        collection = TaskCollection(
            name=name.strip(),
            description=description.strip(),
            import_date=date.today(),
            is_active=False
        )
        db.add(collection)
        db.commit()
        return redirect("/collections?success=Workspace created")
    finally:
        close_db(db)

@app.get("/collections/{collection_id}/edit", response_class=HTMLResponse)
def collections_edit(request: Request, collection_id: int) -> typing.Any:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        collection = db.query(TaskCollection).get(collection_id)
        if not collection:
            return redirect("/collections?error=Workspace not found")
        return render(request, "collection_form.html", {"collection": collection}, user)
    finally:
        close_db(db)

@app.post("/collections/{collection_id}/edit")
def collections_update(
    request: Request,
    collection_id: int,
    name: str = Form(...),
    description: str = Form(""),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        collection = db.query(TaskCollection).get(collection_id)
        if not collection:
            return redirect("/collections?error=Workspace not found")

        collection.name = name.strip()
        collection.description = description.strip()
        db.commit()
        return redirect("/collections?success=Workspace updated")
    finally:
        close_db(db)

@app.post("/collections/{collection_id}/delete")
def collections_delete(request: Request, collection_id: int) -> RedirectResponse:
    print(f'--- DELETING {collection_id} ---', flush=True)
    db = get_db()
    try:
        user = require_manager(request, db)
        if isinstance(user, RedirectResponse):
            return user
        collection = db.query(TaskCollection).get(collection_id)
        if not collection:
            return redirect("/collections?error=Workspace not found")
            
        was_active = collection.is_active

        # Delete corresponding import if this was auto-generated
        if collection.description and collection.description.startswith("Auto-generated workspace for import "):
            try:
                import_id = int(collection.description.replace("Auto-generated workspace for import ", ""))
                record = db.query(WorkbookImport).filter(WorkbookImport.id == import_id).first()
                if record:
                    if record.stored_path:
                        import os
                        try:
                            if os.path.exists(record.stored_path):
                                os.remove(record.stored_path)
                        except OSError:
                            pass
                    db.delete(record)
            except ValueError:
                pass

        db.delete(collection)
        
        # If the deleted workspace was active, activate another one if available
        if was_active:
            fallback = db.query(TaskCollection).filter(TaskCollection.id != collection_id).order_by(TaskCollection.created_at.desc()).first()
            if fallback:
                fallback.is_active = True
                
        db.commit()
        
        if request.headers.get("HX-Request"):
            return HTMLResponse(status_code=200, headers={"HX-Refresh": "true"})
            
        return redirect("/collections?success=Workspace deleted")
    finally:
        close_db(db)

@app.post("/collections/{collection_id}/activate")
def collections_activate(request: Request, collection_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        collection = db.query(TaskCollection).get(collection_id)
        if not collection:
            return redirect("/collections?error=Workspace not found")

        # Deactivate all others
        db.query(TaskCollection).update({TaskCollection.is_active: False})
        # Activate this one
        collection.is_active = True
        db.commit()
        return redirect("/collections?success=Active Workspace switched")
    finally:
        close_db(db)
