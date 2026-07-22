"""Responsive dashboard web application."""

from __future__ import annotations

import json
import typing
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
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
    WhatsAppLog,
    WorkbookImport,
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
    send_test_whatsapp,
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

app.include_router(auth_router)

def parse_json_values(record) -> dict[str, object]:
    """Parse a module row JSON payload."""
    try:
        values = json.loads(record.values_json)
    except json.JSONDecodeError:
        return {}
    return values if isinstance(values, dict) else {}

@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> RedirectResponse:
    """Redirect to the dashboard or login."""
    db = get_db()
    try:
        user = current_user(request, db)
        return redirect("/dashboard" if user else "/login")
    finally:
        close_db(db)


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
        activities = db.query(ActivityRecord).filter(ActivityRecord.is_active.is_(True)).all()
        pending_count = sum(1 for row in activities if (row.status or "").strip().casefold() != "done")
        done_count = sum(1 for row in activities if (row.status or "").strip().casefold() == "done")
        last_run = db.query(ReminderRun).order_by(ReminderRun.created_at.desc()).first()
        last_email = db.query(EmailLog).order_by(EmailLog.created_at.desc()).first()
        last_whatsapp = db.query(WhatsAppLog).order_by(WhatsAppLog.created_at.desc()).first()
        modules = db.query(Module).order_by(Module.name.asc()).limit(8).all()

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
                "module_count": db.query(Module).count(),
                "last_run": last_run,
                "last_email": last_email,
                "last_whatsapp": last_whatsapp,
                "modules": modules,
            },
            user,
        )
    finally:
        close_db(db)


@app.get("/activities", response_class=HTMLResponse)
def activities(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        rows = (
            db.query(ActivityRecord)
            .filter(ActivityRecord.is_active.is_(True))
            .order_by(ActivityRecord.sort_order.asc(), ActivityRecord.id.asc())
            .all()
        )
        return render(request, "activities.html", {"activities": rows}, user)
    finally:
        close_db(db)


@app.get("/activities/new", response_class=HTMLResponse)
def activity_new(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        modules = db.query(Module).order_by(Module.name.asc()).all()
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.display_name.asc()).all()
        return render(
            request,
            "activity_form.html",
            {"activity": None, "modules": modules, "users": users, "frequencies": FREQUENCIES},
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
    linked_module_id: str = Form(""),
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
                linked_module_id=int(linked_module_id) if linked_module_id else None,
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
        modules = db.query(Module).order_by(Module.name.asc()).all()
        users = db.query(User).filter(User.is_active.is_(True)).order_by(User.display_name.asc()).all()
        return render(
            request,
            "activity_form.html",
            {"activity": activity, "modules": modules, "users": users, "frequencies": FREQUENCIES},
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
    linked_module_id: str = Form(""),
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
        row.linked_module_id = int(linked_module_id) if linked_module_id else None
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
def activity_delete(request: Request, activity_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        row = db.query(ActivityRecord).filter(ActivityRecord.id == activity_id).first()
        if row:
            row.is_active = False
            db.commit()
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


@app.get("/modules", response_class=HTMLResponse)
def modules(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        rows = db.query(Module).order_by(Module.name.asc()).all()
        return render(request, "modules.html", {"modules": rows}, user)
    finally:
        close_db(db)


@app.get("/modules/{module_id}", response_class=HTMLResponse)
def module_detail(request: Request, module_id: int) -> typing.Any:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        module = db.query(Module).filter(Module.id == module_id).first()
        if module is None:
            return redirect("/modules?error=Module not found")
        fields = sorted(module.fields, key=lambda item: item.position)
        records = sorted(module.records, key=lambda item: item.row_number)
        record_rows = [{"record": record, "values": parse_json_values(record)} for record in records]
        return render(
            request,
            "module_detail.html",
            {"module": module, "fields": fields, "record_rows": record_rows},
            user,
        )
    finally:
        close_db(db)


@app.post("/modules/{module_id}/save")
async def module_save(request: Request, module_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        module = db.query(Module).filter(Module.id == module_id).first()
        if module is None:
            return redirect("/modules?error=Module not found")

        form = await request.form()
        fields = sorted(module.fields, key=lambda item: item.position)
        for record in module.records:
            values = {}
            for field in fields:
                values[field.name] = str(form.get(f"cell_{record.id}_{field.id}", "")).strip()
            record.values_json = json.dumps(values, ensure_ascii=False)
        db.commit()
        return redirect(f"/modules/{module_id}?notice=Module saved")
    finally:
        close_db(db)


@app.post("/modules/{module_id}/rows/new")
def module_add_row(request: Request, module_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        module = db.query(Module).filter(Module.id == module_id).first()
        if module is None:
            return redirect("/modules?error=Module not found")
        fields = sorted(module.fields, key=lambda item: item.position)
        values = {field.name: "" for field in fields}
        next_row = (max((record.row_number for record in module.records), default=0) + 1)
        db.add(ModuleDataRecord(module_id=module.id, row_number=next_row, values_json=json.dumps(values)))
        db.commit()
        return redirect(f"/modules/{module_id}?notice=Row added")
    finally:
        close_db(db)


@app.post("/modules/{module_id}/rows/{record_id}/delete")
def module_delete_row(request: Request, module_id: int, record_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        record = (
            db.query(ModuleDataRecord)
            .filter(ModuleDataRecord.id == record_id, ModuleDataRecord.module_id == module_id)
            .first()
        )
        if record:
            db.delete(record)
            db.commit()
        return redirect(f"/modules/{module_id}?notice=Row deleted")
    finally:
        close_db(db)


@app.post("/modules/{module_id}/delete")
def module_delete(request: Request, module_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        module = db.query(Module).filter(Module.id == module_id).first()
        if module:
            db.delete(module)
            db.commit()
        return redirect("/modules?notice=Module deleted")
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


@app.get("/settings/whatsapp", response_class=HTMLResponse)
def whatsapp_settings(request: Request) -> typing.Any:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        active = effective_settings(db, settings)
        return render(
            request,
            "settings_whatsapp.html",
            {"settings": active, "masked_token": masked(active.whatsapp_access_token)},
            user,
        )
    finally:
        close_db(db)


@app.post("/settings/whatsapp")
def whatsapp_settings_save(
    request: Request,
    whatsapp_enabled: str = Form("false"),
    whatsapp_access_token: str = Form(""),
    whatsapp_phone_number_id: str = Form(""),
    whatsapp_recipient_number: str = Form(""),
    whatsapp_template_name: str = Form(""),
    whatsapp_language_code: str = Form(""),
    whatsapp_graph_api_url: str = Form(""),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        set_setting(db, "WHATSAPP_ENABLED", "true" if whatsapp_enabled == "true" else "false")
        if whatsapp_access_token.strip():
            set_setting(db, "WHATSAPP_ACCESS_TOKEN", whatsapp_access_token.strip(), is_secret=True)
        set_setting(db, "WHATSAPP_PHONE_NUMBER_ID", whatsapp_phone_number_id.strip())
        set_setting(db, "WHATSAPP_RECIPIENT_NUMBER", whatsapp_recipient_number.strip())
        set_setting(db, "WHATSAPP_TEMPLATE_NAME", whatsapp_template_name.strip())
        set_setting(db, "WHATSAPP_LANGUAGE_CODE", whatsapp_language_code.strip())
        set_setting(db, "WHATSAPP_GRAPH_API_URL", whatsapp_graph_api_url.strip())
        db.commit()
        return redirect("/settings/whatsapp?notice=WhatsApp settings saved")
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


@app.post("/reminders/send-test-whatsapp")
def reminders_send_test_whatsapp(request: Request) -> RedirectResponse:
    db = get_db()
    try:
        user = require_admin(request, db)
        if isinstance(user, RedirectResponse):
            return user
        result = send_test_whatsapp(db, settings, logger)
        db.commit()
        target = "notice" if result.success else "error"
        return redirect(f"/reminders/preview?{target}={result.message}")
    finally:
        close_db(db)


