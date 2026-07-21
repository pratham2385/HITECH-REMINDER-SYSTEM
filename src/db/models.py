"""SQLAlchemy models for dashboard persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    """Dashboard user account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True) # Kept for legacy compatibility if needed
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="employee")
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    email_verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("ActivityRecord", back_populates="assigned_user")


class ActivityRecord(Base):
    """Reminder activity maintained from the dashboard."""

    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    activity = Column(String(255), nullable=False)
    frequency = Column(String(50), nullable=False)
    date_value = Column(String(100), nullable=True)
    link = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    remark = Column(Text, nullable=True)
    linked_module_id = Column(Integer, ForeignKey("modules.id", ondelete="SET NULL"), nullable=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    email_enabled = Column(Boolean, nullable=False, default=True)
    whatsapp_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    linked_module = relationship("Module", back_populates="activities")
    assigned_user = relationship("User", back_populates="activities")


class Module(Base):
    """Editable dashboard module created from an Excel sheet or manually."""

    __tablename__ = "modules"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    source_sheet_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    fields = relationship("ModuleField", back_populates="module", cascade="all, delete-orphan")
    records = relationship("ModuleDataRecord", back_populates="module", cascade="all, delete-orphan")
    activities = relationship("ActivityRecord", back_populates="linked_module")


class ModuleField(Base):
    """Column definition for a flexible module table."""

    __tablename__ = "module_fields"

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, default=0)

    module = relationship("Module", back_populates="fields")


class ModuleDataRecord(Base):
    """One editable row in a flexible module table."""

    __tablename__ = "module_records"

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    row_number = Column(Integer, nullable=False, default=0)
    values_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    module = relationship("Module", back_populates="records")
    assigned_user = relationship("User")


class WorkbookImport(Base):
    """History row for an uploaded or CLI-imported workbook."""

    __tablename__ = "workbook_imports"

    id = Column(Integer, primary_key=True)
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    sheet_count = Column(Integer, nullable=False, default=0)
    row_count = Column(Integer, nullable=False, default=0)
    imported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    sheets = relationship("ImportedSheet", back_populates="workbook_import", cascade="all, delete-orphan")


class ImportedSheet(Base):
    """Imported sheet metadata linked to the generated module."""

    __tablename__ = "imported_sheets"

    id = Column(Integer, primary_key=True)
    workbook_import_id = Column(Integer, ForeignKey("workbook_imports.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True)
    sheet_name = Column(String(255), nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)

    workbook_import = relationship("WorkbookImport", back_populates="sheets")
    module = relationship("Module")


class ReminderRun(Base):
    """Execution history for daily reminder jobs."""

    __tablename__ = "reminder_runs"

    id = Column(Integer, primary_key=True)
    run_date = Column(String(20), nullable=False, index=True)
    activity_count = Column(Integer, nullable=False, default=0)
    email_status = Column(String(30), nullable=False, default="not_sent")
    whatsapp_status = Column(String(30), nullable=False, default="not_sent")
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class EmailLog(Base):
    """Email delivery audit log."""

    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True)
    reminder_run_id = Column(Integer, ForeignKey("reminder_runs.id"), nullable=True)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    success = Column(Boolean, nullable=False, default=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class WhatsAppLog(Base):
    """WhatsApp delivery audit log."""

    __tablename__ = "whatsapp_logs"

    id = Column(Integer, primary_key=True)
    reminder_run_id = Column(Integer, ForeignKey("reminder_runs.id"), nullable=True)
    recipient = Column(String(50), nullable=False)
    template_name = Column(String(100), nullable=False)
    success = Column(Boolean, nullable=False, default=False)
    provider_message_id = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class NotificationSetting(Base):
    """Editable notification configuration stored by the dashboard."""

    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")
    is_secret = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit log for tracking user actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User")


class PasswordResetToken(Base):
    """Tokens for password reset."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="password_reset_tokens")


class EmailVerificationToken(Base):
    """Tokens for email verification."""

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="email_verification_tokens")


class LoginHistory(Base):
    """History of login attempts for rate limiting and auditing."""

    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(50), nullable=False) # e.g. success, failed, locked
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="login_history")

