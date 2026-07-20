"""Responsive dashboard web application."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

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
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
SESSION_COOKIE = "activity_dashboard_session"
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

def cell_display(value: object) -> str:
    """Display a flexible imported cell value."""

    if isinstance(value, dict):
        return str(value.get("value") or "")
    if value is None:
        return ""
    return str(value)


def cell_link(value: object) -> str:
    """Return a hyperlink target for imported cell values."""

    if isinstance(value, dict):
        return str(value.get("link") or "")
    return ""


templates.env.filters["cell_display"] = cell_display
templates.env.filters["cell_link"] = cell_link


def get_db() -> Session:
    """Return a new request-scoped database session."""

    return get_session_factory(settings)()


def close_db(db: Session) -> None:
    """Close a request-scoped database session."""

    db.close()


def redirect(path: str) -> RedirectResponse:
    """Return a standard POST-safe redirect."""

    return RedirectResponse(path, status_code=303)


def current_user(request: Request, db: Session) -> User | None:
    """Return the logged-in user from the signed cookie."""

    cookie_value = request.cookies.get(SESSION_COOKIE)
    if not cookie_value:
        return None
    user_id = verify_session(cookie_value, settings.secret_key)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()


def user_context(user: User | None) -> dict[str, object] | None:
    """Return a safe template context for a user."""

    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "is_owner": user.role == "owner",
        "can_edit": user.role in {"owner", "staff"},
    }


def render(
    request: Request,
    template_name: str,
    context: dict[str, object] | None = None,
    user: User | None = None,
) -> HTMLResponse:
    """Render a dashboard template."""

    payload = {
        "request": request,
        "app_name": APP_NAME,
        "user": user_context(user),
        "notice": request.query_params.get("notice", ""),
        "error": request.query_params.get("error", ""),
    }
    if context:
        payload.update(context)
    return templates.TemplateResponse(template_name, payload)


def require_login(request: Request, db: Session) -> User | Response:
    user = current_user(request, db)
    if user is None:
        return redirect("/login")
    return user


def require_owner(request: Request, db: Session) -> User | Response:
    user = require_login(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role != "owner":
        return redirect("/dashboard?error=Owner access required")
    return user


def require_editor(request: Request, db: Session) -> User | Response:
    user = require_login(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role not in {"owner", "staff"}:
        return redirect("/dashboard?error=Edit access required")
    return user


def parse_json_values(record: ModuleDataRecord) -> dict[str, object]:
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


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return render(request, "login.html")


@app.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    db = get_db()
    try:
        user = db.query(User).filter(User.username == username.strip(), User.is_active.is_(True)).first()
        if user is None or not verify_password(password, user.password_hash):
            return redirect("/login?error=Invalid username or password")
        response = redirect("/dashboard")
        response.set_cookie(
            SESSION_COOKIE,
            sign_session(user.id, settings.secret_key),
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 12,
        )
        return response
    finally:
        close_db(db)


@app.post("/logout")
def logout() -> RedirectResponse:
    response = redirect("/login?notice=Logged out")
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request) -> Response:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user

        today = date.today()
        due_records = get_due_activity_records(db, today, logger)
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
def activities(request: Request) -> Response:
    db = get_db()
    try:
        user = require_login(request, db)
        if isinstance(user, RedirectResponse):
            return user
        rows = (
            db.query(ActivityRecord)
            .options(joinedload(ActivityRecord.assignee), joinedload(ActivityRecord.linked_module))
            .filter(ActivityRecord.is_active.is_(True))
            .order_by(ActivityRecord.sort_order.asc(), ActivityRecord.id.asc())
            .all()
        )
        return render(request, "activities.html", {"activities": rows}, user)
    finally:
        close_db(db)


@app.get("/activities/new", response_class=HTMLResponse)
def activity_new(request: Request) -> Response:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        modules = db.query(Module).order_by(Module.name.asc()).all()
        return render(
            request,
            "activity_form.html",
            {"activity": None, "modules": modules, "frequencies": FREQUENCIES},
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
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        sort_order = db.query(ActivityRecord).count() + 1
        db.add(
            ActivityRecord(
                activity=activity.strip(),
                frequency=frequency.strip(),
                date_value=date_value.strip(),
                link=link.strip(),
                status=status.strip(),
                remark=remark.strip(),
                linked_module_id=int(linked_module_id) if linked_module_id else None,
                sort_order=sort_order,
                is_active=True,
            )
        )
        db.commit()
        return redirect("/activities?notice=Activity created")
    finally:
        close_db(db)


@app.get("/activities/{activity_id}/edit", response_class=HTMLResponse)
def activity_edit(request: Request, activity_id: int) -> Response:
    db = get_db()
    try:
        user = require_editor(request, db)
        if isinstance(user, RedirectResponse):
            return user
        activity = db.query(ActivityRecord).filter(ActivityRecord.id == activity_id).first()
        if activity is None:
            return redirect("/activities?error=Activity not found")
        modules = db.query(Module).order_by(Module.name.asc()).all()
        return render(
            request,
            "activity_form.html",
            {"activity": activity, "modules": modules, "frequencies": FREQUENCIES},
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
        db.commit()
        return redirect("/activities?notice=Activity updated")
    finally:
        close_db(db)


@app.post("/activities/{activity_id}/delete")
def activity_delete(request: Request, activity_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        row = db.query(ActivityRecord).filter(ActivityRecord.id == activity_id).first()
        if row:
            row.is_active = False
            db.commit()
        return redirect("/activities?notice=Activity deleted")
    finally:
        close_db(db)


@app.get("/modules", response_class=HTMLResponse)
def modules(request: Request) -> Response:
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
def module_detail(request: Request, module_id: int) -> Response:
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
        user = require_owner(request, db)
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
def imports(request: Request) -> Response:
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
def import_new(request: Request) -> Response:
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
def import_detail(request: Request, import_id: int) -> Response:
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
def email_settings(request: Request) -> Response:
    db = get_db()
    try:
        user = require_owner(request, db)
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
        user = require_owner(request, db)
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
def whatsapp_settings(request: Request) -> Response:
    db = get_db()
    try:
        user = require_owner(request, db)
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
        user = require_owner(request, db)
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
def reminders_preview(request: Request, preview_date: str = None) -> Response:
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
        # It's already in reminder_service.py as build_preview_email(session, logger, run_date)
        
        from src.services.reminder_service import get_due_domain_activities, build_preview_email
        due_activities = get_due_domain_activities(db, logger, target_date)
        content = build_preview_email(db, logger, target_date)
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
        user = require_owner(request, db)
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
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        result = send_test_whatsapp(db, settings, logger)
        db.commit()
        target = "notice" if result.success else "error"
        return redirect(f"/reminders/preview?{target}={result.message}")
    finally:
        close_db(db)


@app.get("/users", response_class=HTMLResponse)
def users(request: Request) -> Response:
    db = get_db()
    try:
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        rows = db.query(User).order_by(User.username.asc()).all()
        return render(request, "users.html", {"users": rows, "roles": ROLES}, user)
    finally:
        close_db(db)


@app.get("/users/new", response_class=HTMLResponse)
def user_new(request: Request) -> Response:
    db = get_db()
    try:
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        return render(request, "user_form.html", {"account": None, "roles": ROLES}, user)
    finally:
        close_db(db)


@app.post("/users/new")
def user_create(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        if role not in ROLES:
            return redirect("/users/new?error=Invalid role")
        if db.query(User).filter(User.username == username.strip()).first():
            return redirect("/users/new?error=Username already exists")
        db.add(
            User(
                username=username.strip(),
                display_name=display_name.strip(),
                role=role,
                password_hash=hash_password(password),
                is_active=True,
            )
        )
        db.commit()
        return redirect("/users?notice=User created")
    finally:
        close_db(db)


@app.get("/users/{user_id}/edit", response_class=HTMLResponse)
def user_edit(request: Request, user_id: int) -> Response:
    db = get_db()
    try:
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        account = db.query(User).filter(User.id == user_id).first()
        if account is None:
            return redirect("/users?error=User not found")
        return render(request, "user_form.html", {"account": account, "roles": ROLES}, user)
    finally:
        close_db(db)


@app.post("/users/{user_id}/edit")
def user_update(
    request: Request,
    user_id: int,
    username: str = Form(...),
    display_name: str = Form(...),
    role: str = Form(...),
    password: str = Form(""),
    is_active: str = Form("false"),
) -> RedirectResponse:
    db = get_db()
    try:
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        account = db.query(User).filter(User.id == user_id).first()
        if account is None:
            return redirect("/users?error=User not found")
        account.username = username.strip()
        account.display_name = display_name.strip()
        account.role = role if role in ROLES else account.role
        account.is_active = is_active == "true"
        if password.strip():
            account.password_hash = hash_password(password)
        db.commit()
        return redirect("/users?notice=User updated")
    finally:
        close_db(db)

@app.post("/users/{user_id}/delete")
def user_delete(request: Request, user_id: int) -> RedirectResponse:
    db = get_db()
    try:
        user = require_owner(request, db)
        if isinstance(user, RedirectResponse):
            return user
        if user.id == user_id:
            return redirect("/users?error=You cannot delete your own account")
        account = db.query(User).filter(User.id == user_id).first()
        if account is None:
            return redirect("/users?error=User not found")
        account.is_active = False
        db.commit()
        return redirect("/users?notice=User deleted")
    finally:
        close_db(db)


