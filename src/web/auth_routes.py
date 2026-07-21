"""Authentication routes for login, signup, and account recovery."""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.db.models import User, PasswordResetToken, EmailVerificationToken
from src.services.auth_service import AuthService
from src.security import hash_password, verify_password, sign_session, SESSION_MAX_AGE_SECONDS
from src.config.settings import load_settings
from src.web.app_deps import render, get_db, require_login, require_admin, redirect_with_msg, redirect
from sqlalchemy.exc import IntegrityError
from src.web.csrf import generate_csrf_token, verify_csrf_token # We'll create this

router = APIRouter()
settings = load_settings()
SESSION_COOKIE = "activity_dashboard_session"

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "login.html", csrf_token=generate_csrf_token(request))

@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/login", "Invalid CSRF token", "error")
        
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    user = db.query(User).filter(User.email == email.strip().lower(), User.is_active.is_(True)).first()
    
    if user and AuthService.is_account_locked(db, user.id):
        AuthService.record_login_attempt(db, user.id, client_ip, user_agent, "locked")
        return redirect_with_msg("/login", "Account locked due to too many failed attempts. Try again later.", "error")

    if user is None or not verify_password(password, user.password_hash):
        if user:
            AuthService.record_login_attempt(db, user.id, client_ip, user_agent, "failed")
        return redirect_with_msg("/login", "Invalid email or password.", "error")
        
    if not user.email_verified:
        return render(
            request, 
            "login.html", 
            csrf_token=generate_csrf_token(request), 
            error="Please verify your email before logging in.", 
            unverified_email=user.email
        )

    AuthService.record_login_attempt(db, user.id, client_ip, user_agent, "success")
    
    # Check if must change password
    if user.must_change_password:
        response = redirect_with_msg("/profile?force_change=1", "You must change your default password.", "notice")
    else:
        response = redirect_with_msg("/dashboard", "Logged in successfully.", "success")
        
    # Cookie Max Age
    max_age = SESSION_MAX_AGE_SECONDS * 30 if remember else SESSION_MAX_AGE_SECONDS
    
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user.id, settings.secret_key),
        httponly=True,
        samesite="lax",
        max_age=max_age,
    )
    return response


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return render(request, "signup.html", csrf_token=generate_csrf_token(request))


@router.post("/signup")
def signup_submit(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/signup", "Invalid CSRF token", "error")

    if not email.strip():
        return redirect_with_msg("/signup", "Email is required.", "error")
        
    if not password.strip():
        return redirect_with_msg("/signup", "Password is required.", "error")

    if password != confirm_password:
        return redirect_with_msg("/signup", "Passwords do not match.", "error")
        
    is_valid, msg = AuthService.validate_password_strength(password)
    if not is_valid:
        return redirect_with_msg("/signup", msg, "error")

    email = email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        return redirect_with_msg("/signup", "Email is already registered.", "error")
        
    valid_roles = {"admin", "manager", "employee"}
    if role not in valid_roles:
        return redirect_with_msg("/signup", "Invalid role.", "error")

    new_user = User(
        username=email, # fallback
        email=email,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        email_verified=True
    )
    db.add(new_user)
    try:
        db.flush() # get ID
    except IntegrityError:
        db.rollback()
        return redirect_with_msg("/signup", "Email is already registered.", "error")
    
    db.commit()
    return redirect_with_msg("/login", "Registration successful. You can now log in.", "success")


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    verification_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token,
        EmailVerificationToken.used.is_(False),
        EmailVerificationToken.expires_at > datetime.utcnow()
    ).first()
    
    if not verification_token:
        return redirect_with_msg("/login", "Invalid or expired verification link.", "error")
        
    user = verification_token.user
    user.email_verified = True
    verification_token.used = True
    db.commit()
    
    return redirect_with_msg("/login", "Email verified successfully! You can now log in.", "success")


@router.post("/resend-verification")
def resend_verification(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/login", "Invalid CSRF token", "error")
        
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if user and not user.email_verified:
        token = AuthService.create_email_verification_token(db, user)
        base_url = str(request.base_url).rstrip("/")
        try:
            AuthService.send_verification_email(settings, user, token, base_url)
            return redirect_with_msg("/login", "Verification email sent! Please check your inbox.", "success")
        except Exception:
            return redirect_with_msg("/login", "Failed to send verification email. Please try again later.", "error")
            
    return redirect_with_msg("/login", "User not found or already verified.", "notice")


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return render(request, "forgot_password.html", csrf_token=generate_csrf_token(request))


@router.post("/forgot-password")
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/forgot-password", "Invalid CSRF token", "error")

    user = db.query(User).filter(User.email == email.strip().lower(), User.is_active.is_(True)).first()
    if user:
        token = AuthService.create_password_reset_token(db, user)
        try:
            base_url = str(request.base_url).rstrip("/")
            AuthService.send_password_reset_email(settings, user, token, base_url)
        except Exception:
            pass
            
    # Always return success to prevent email enumeration
    return redirect_with_msg("/forgot-password", "If your email is registered, a password reset link has been sent.", "success")


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str, db: Session = Depends(get_db)):
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used.is_(False),
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_token:
        return redirect_with_msg("/forgot-password", "Invalid or expired reset link.", "error")
        
    return render(request, "reset_password.html", csrf_token=generate_csrf_token(request), token=token)


@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/forgot-password", "Invalid CSRF token", "error")

    if password != confirm_password:
        return render(request, "reset_password.html", csrf_token=generate_csrf_token(request), token=token, error="Passwords do not match.")

    is_valid, msg = AuthService.validate_password_strength(password)
    if not is_valid:
        return render(request, "reset_password.html", csrf_token=generate_csrf_token(request), token=token, error=msg)

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used.is_(False),
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_token:
        return redirect_with_msg("/forgot-password", "Invalid or expired reset link.", "error")
        
    user = reset_token.user
    user.password_hash = hash_password(password)
    user.must_change_password = False
    reset_token.used = True
    db.commit()
    
    return redirect_with_msg("/login", "Password reset successfully. You can now log in.", "success")


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if isinstance(user, RedirectResponse): return user
    return render(request, "profile.html", user=user, csrf_token=generate_csrf_token(request))

@router.post("/profile/password")
def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    user = require_login(request, db)
    if isinstance(user, RedirectResponse): return user
    
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/profile", "Invalid CSRF token", "error")
        
    if not verify_password(current_password, user.password_hash):
        return redirect_with_msg("/profile", "Incorrect current password", "error")
        
    if new_password != confirm_password:
        return redirect_with_msg("/profile", "New passwords do not match", "error")
        
    is_valid, msg = AuthService.validate_password_strength(new_password)
    if not is_valid:
        return redirect_with_msg("/profile", msg, "error")
        
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()
    
    return redirect_with_msg("/profile", "Password updated successfully", "success")

@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if isinstance(user, RedirectResponse): return user
    
    users = db.query(User).order_by(User.id.desc()).all()
    # Provide ROLES to the template
    ROLES = ["admin", "manager", "employee"]
    return render(request, "users.html", user=user, users=users, roles=ROLES, csrf_token=generate_csrf_token(request))



@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def user_edit(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if isinstance(user, RedirectResponse): return user
    
    account = db.query(User).filter(User.id == user_id).first()
    if account is None:
        return redirect_with_msg("/users", "User not found", "error")
        
    ROLES = ["admin", "manager", "employee"]
    return render(request, "user_form.html", user=user, account=account, roles=ROLES, csrf_token=generate_csrf_token(request))


@router.post("/users/{user_id}/edit")
def user_update(
    request: Request,
    user_id: int,
    username: str = Form(...),
    display_name: str = Form(...),
    role: str = Form(...),
    csrf_token: str = Form(...),
    password: str = Form(""),
    is_active: str = Form("false"),
    db: Session = Depends(get_db)
):
    user = require_admin(request, db)
    if isinstance(user, RedirectResponse): return user
    
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg(f"/users/{user_id}/edit", "Invalid CSRF token", "error")
        
    account = db.query(User).filter(User.id == user_id).first()
    if account is None:
        return redirect_with_msg("/users", "User not found", "error")
        
    ROLES = ["admin", "manager", "employee"]
    account.username = username.strip()
    account.email = username.strip()
    account.display_name = display_name.strip()
    if role in ROLES:
        account.role = role
    account.is_active = is_active == "true"
    if password.strip():
        account.password_hash = hash_password(password)
        
    db.commit()
    return redirect_with_msg("/users", "User updated successfully", "success")


@router.post("/users/{user_id}/delete")
def user_delete(request: Request, user_id: int, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if isinstance(user, RedirectResponse): return user
    
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/users", "Invalid CSRF token", "error")
        
    if user.id == user_id:
        return redirect_with_msg("/users", "You cannot delete yourself.", "error")
        
    account = db.query(User).filter(User.id == user_id).first()
    if account is None:
        return redirect_with_msg("/users", "User not found", "error")
        
    db.delete(account)
    db.commit()
    return redirect_with_msg("/users", "User deleted successfully", "success")

@router.post("/users/{user_id}/toggle")
def toggle_user(request: Request, user_id: int, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if isinstance(user, RedirectResponse): return user
    
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/users", "Invalid CSRF token", "error")
        
    if user.id == user_id:
        return redirect_with_msg("/users", "You cannot deactivate yourself.", "error")
        
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.is_active = not target_user.is_active
        db.commit()
        return redirect_with_msg("/users", f"User {'activated' if target_user.is_active else 'deactivated'} successfully", "success")
        
    return redirect_with_msg("/users", "User not found", "error")


@router.post("/users/{user_id}/verify")
def toggle_user_verify(request: Request, user_id: int, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if isinstance(user, RedirectResponse): return user
    
    if not verify_csrf_token(request, csrf_token):
        return redirect_with_msg("/users", "Invalid CSRF token", "error")
        
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.email_verified = not target_user.email_verified
        db.commit()
        status_msg = "verified" if target_user.email_verified else "unverified"
        return redirect_with_msg("/users", f"User {status_msg} successfully", "success")
        
    return redirect_with_msg("/users", "User not found", "error")

@router.post("/logout")
def logout() -> RedirectResponse:
    response = redirect_with_msg("/login", "Logged out successfully.", "notice")
    response.delete_cookie(SESSION_COOKIE)
    return response

# Helper for redirect with messages
def redirect_with_msg(url: str, msg: str, msg_type: str = "notice"):
    from fastapi.responses import RedirectResponse
    import urllib.parse
    return RedirectResponse(f"{url}?{msg_type}={urllib.parse.quote(msg)}", status_code=303)
