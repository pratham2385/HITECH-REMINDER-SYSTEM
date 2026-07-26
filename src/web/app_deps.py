"""Shared web dependencies and helpers."""

from __future__ import annotations
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.config.settings import APP_NAME, load_settings, TEMPLATE_DIR
from src.db.models import User
from src.security import verify_session
import typing

settings = load_settings()
SESSION_COOKIE = "activity_dashboard_session"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

from src.db.session import get_session_factory

def get_db() -> Session:
    """Return a new request-scoped database session."""
    return get_session_factory(settings)()

def close_db(db: Session) -> None:
    """Close a request-scoped database session."""
    db.close()

def cell_display(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("value") or "")
    if value is None:
        return ""
    return str(value)

def cell_link(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("link") or "")
    return ""

templates.env.filters["cell_display"] = cell_display
templates.env.filters["cell_link"] = cell_link

def redirect(path: str) -> RedirectResponse:
    """Return a standard POST-safe redirect."""
    return RedirectResponse(path, status_code=303)

def redirect_with_msg(url: str, msg: str, msg_type: str = "notice"):
    import urllib.parse
    return RedirectResponse(f"{url}?{msg_type}={urllib.parse.quote(msg)}", status_code=303)


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
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "is_owner": user.role in {"owner", "admin"},
        "can_edit": user.role in {"owner", "admin", "manager", "staff"},
        "is_admin": user.role == "admin",
        "is_manager": user.role == "manager",
    }


def render(
    request: Request,
    template_name: str,
    context: dict[str, object] | None = None,
    user: User | None = None,
    **kwargs
) -> HTMLResponse:
    """Render a dashboard template."""
    payload = {
        "request": request,
        "app_name": APP_NAME,
        "user": user_context(user),
        "notice": request.query_params.get("notice", ""),
        "error": request.query_params.get("error", ""),
        "success": request.query_params.get("success", ""),
    }
    if context:
        payload.update(context)
    if kwargs:
        payload.update(kwargs)
    return templates.TemplateResponse(template_name, payload)


def require_login(request: Request, db: Session) -> typing.Union[User, RedirectResponse]:
    user = current_user(request, db)
    if user is None:
        return redirect("/login?error=Please log in to continue")
    return user


def require_admin(request: Request, db: Session) -> typing.Union[User, RedirectResponse]:
    user = require_login(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role not in {"admin", "owner"}:
        return redirect("/dashboard?error=Admin access required")
    return user


def require_manager(request: Request, db: Session) -> typing.Union[User, RedirectResponse]:
    user = require_login(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role not in {"admin", "owner", "manager"}:
        return redirect("/dashboard?error=Manager access required")
    return user

def require_editor(request: Request, db: Session) -> typing.Union[User, RedirectResponse]:
    return require_manager(request, db)
