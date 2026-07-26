"""Excel import service for turning workbooks into dashboard modules."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.models import (
    ActivityRecord,
    ImportedSheet,
    Module,
    ModuleDataRecord,
    ModuleField,
    WorkbookImport,
    User,
    NotificationSetting,
)
from src.utils.helpers import clean_string


@dataclass(frozen=True, slots=True)
class SheetPreview:
    """Preview metadata for one workbook sheet."""

    name: str
    columns: list[str]
    row_count: int
    sample_rows: list[dict[str, Any]]
    is_activity_like: bool


@dataclass(frozen=True, slots=True)
class WorkbookPreview:
    """Preview metadata for one workbook."""

    filename: str
    sheet_count: int
    row_count: int
    sheets: list[SheetPreview]


def _load_workbook(path: Path):
    try:
        from openpyxl import load_workbook
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing required dependency: openpyxl. Run `pip install -r requirements.txt`.") from exc

    return load_workbook(path, data_only=True, read_only=False)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _cell_value(cell: Any) -> Any:
    value = _json_value(cell.value)
    if cell.hyperlink and cell.hyperlink.target:
        return {"value": value if value is not None else cell.hyperlink.target, "link": cell.hyperlink.target}
    return value


def _display_value(value: Any) -> str:
    if isinstance(value, dict):
        return clean_string(value.get("value", ""))
    return clean_string(value)


def _make_headers(raw_headers: list[Any], column_count: int) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}

    for index in range(column_count):
        base = _display_value(raw_headers[index]) if index < len(raw_headers) else ""
        header = base or f"Column {index + 1}"
        if header in seen:
            seen[header] += 1
            header = f"{header} {seen[header]}"
        else:
            seen[header] = 1
        headers.append(header)

    return headers


def _find_header_row(rows: list[list[Any]]) -> int:
    for index, row in enumerate(rows):
        if any(_display_value(value) for value in row):
            return index
    return 0


def _sheet_rows(sheet: Any) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for row in sheet.iter_rows():
        rows.append([_cell_value(cell) for cell in row])
    return rows


def _row_dict(columns: list[str], row: list[Any]) -> dict[str, Any]:
    return {column: row[index] if index < len(row) else None for index, column in enumerate(columns)}


def _is_activity_like(columns: list[str]) -> bool:
    normalized = {column.strip().casefold() for column in columns}
    return {"activity", "frequency", "date"}.issubset(normalized)


class ExcelImportService:
    """Imports uploaded Excel workbooks into modules and activities."""

    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir

    def save_uploaded_file(self, filename: str, source_path: Path) -> Path:
        """Copy an uploaded workbook into the managed upload directory."""

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(filename).name or "workbook.xlsx"
        stored_path = self.upload_dir / f"{uuid4().hex}_{safe_name}"
        shutil.copy2(source_path, stored_path)
        return stored_path

    def preview_workbook(self, workbook_path: Path) -> WorkbookPreview:
        """Return a structured preview of a workbook without importing it."""

        workbook = _load_workbook(workbook_path)
        previews: list[SheetPreview] = []
        total_rows = 0

        for sheet in workbook.worksheets:
            raw_rows = _sheet_rows(sheet)
            if not raw_rows:
                previews.append(SheetPreview(sheet.title, [], 0, [], False))
                continue

            column_count = max((len(row) for row in raw_rows), default=0)
            header_index = _find_header_row(raw_rows)
            columns = _make_headers(raw_rows[header_index] if raw_rows else [], column_count)
            data_rows = raw_rows[header_index + 1 :]
            row_count = sum(1 for row in data_rows if any(_display_value(value) for value in row))
            total_rows += row_count
            sample_rows = [_row_dict(columns, row) for row in data_rows[:5]]

            previews.append(
                SheetPreview(
                    name=sheet.title,
                    columns=columns,
                    row_count=row_count,
                    sample_rows=sample_rows,
                    is_activity_like=_is_activity_like(columns),
                )
            )

        return WorkbookPreview(
            filename=workbook_path.name,
            sheet_count=len(previews),
            row_count=total_rows,
            sheets=previews,
        )

    def create_pending_import(
        self,
        session: Session,
        original_filename: str,
        stored_path: Path,
        imported_by_user_id: int | None,
    ) -> WorkbookImport:
        """Create a pending import history row after upload."""

        preview = self.preview_workbook(stored_path)
        record = WorkbookImport(
            original_filename=original_filename,
            stored_path=str(stored_path),
            status="pending",
            sheet_count=preview.sheet_count,
            row_count=preview.row_count,
            imported_by_user_id=imported_by_user_id,
        )
        session.add(record)
        session.flush()
        return record

    
    def import_workbook(
        self,
        session: Session,
        workbook_import: WorkbookImport,
        import_activity_sheets: bool = True,
    ) -> WorkbookImport:
        """Import workbook sheets based on explicit schema."""

        workbook_path = Path(workbook_import.stored_path)
        workbook = _load_workbook(workbook_path)
        total_rows = 0

        for sheet in workbook.worksheets:
            raw_rows = _sheet_rows(sheet)
            header_index = _find_header_row(raw_rows) if raw_rows else 0
            
            if not raw_rows:
                continue

            column_count = max((len(row) for row in raw_rows), default=0)
            columns = _make_headers(raw_rows[header_index] if raw_rows else [], column_count)
            data_rows = raw_rows[header_index + 1 :] if raw_rows else []
            nonblank_rows = [row for row in data_rows if any(_display_value(value) for value in row)]

            if sheet.title == "Users":
                self._sync_users(session, columns, nonblank_rows)
            elif sheet.title == "Modules":
                self._sync_modules(session, columns, nonblank_rows)
            elif sheet.title == "Activities":
                self._sync_activities(session, columns, nonblank_rows)
            elif sheet.title in ("Reminder_Config", "Email_Settings", "WhatsApp_Settings"):
                self._sync_settings(session, columns, nonblank_rows)
            
            total_rows += len(nonblank_rows)
            session.add(
                ImportedSheet(
                    workbook_import_id=workbook_import.id,
                    module_id=None,
                    sheet_name=sheet.title,
                    row_count=len(nonblank_rows),
                    column_count=len(columns),
                )
            )

        workbook_import.status = "imported"
        workbook_import.sheet_count = len(workbook.worksheets)
        workbook_import.row_count = total_rows
        workbook_import.completed_at = datetime.utcnow()
        session.flush()
        return workbook_import

    def _sync_users(self, session: Session, columns: list[str], rows: list[list[Any]]):
        from src.security import hash_password
        column_lookup = {col.strip().casefold(): col for col in columns}
        def get_value(row_dict, key): return clean_string(row_dict.get(column_lookup.get(key), ""))
        
        for row in rows:
            row_dict = _row_dict(columns, row)
            user_id = get_value(row_dict, "user_id")
            if not user_id: continue
            
            user = session.query(User).filter(User.external_id == user_id).first()
            if not user:
                user = session.query(User).filter(User.username == get_value(row_dict, "email")).first()
            
            if user:
                user.external_id = user_id
                user.display_name = get_value(row_dict, "name")
                user.phone = get_value(row_dict, "phone")
                user.role = (get_value(row_dict, "role") or "viewer").lower()
                user.department = get_value(row_dict, "department")
            else:
                user = User(
                    external_id=user_id,
                    username=get_value(row_dict, "email"),
                    display_name=get_value(row_dict, "name"),
                    phone=get_value(row_dict, "phone"),
                    role=(get_value(row_dict, "role") or "viewer").lower(),
                    department=get_value(row_dict, "department"),
                    password_hash=hash_password("ChangeMe@123")
                )
                session.add(user)
        session.flush()

    def _sync_modules(self, session: Session, columns: list[str], rows: list[list[Any]]):
        column_lookup = {col.strip().casefold(): col for col in columns}
        def get_value(row_dict, key): return clean_string(row_dict.get(column_lookup.get(key), ""))
        
        for row in rows:
            row_dict = _row_dict(columns, row)
            mod_id = get_value(row_dict, "module_id")
            if not mod_id: continue
            
            module = session.query(Module).filter(Module.external_id == mod_id).first()
            if not module:
                module = session.query(Module).filter(Module.name == get_value(row_dict, "module_name")).first()
                
            if module:
                module.external_id = mod_id
                module.name = get_value(row_dict, "module_name")
                module.description = get_value(row_dict, "description")
            else:
                module = Module(
                    external_id=mod_id,
                    name=get_value(row_dict, "module_name") or "Unnamed Module",
                    description=get_value(row_dict, "description")
                )
                session.add(module)
        session.flush()

    def _sync_activities(self, session: Session, columns: list[str], rows: list[list[Any]]):
        column_lookup = {col.strip().casefold(): col for col in columns}
        def get_value(row_dict, key): 
            val = row_dict.get(column_lookup.get(key), "")
            if isinstance(val, dict):
                return clean_string(val.get("value", ""))
            return clean_string(val)
        
        existing_activities = session.query(ActivityRecord).all()
        existing_map = {a.external_id: a for a in existing_activities if a.external_id}
        seen_activities = set()

        for index, row in enumerate(rows, start=1):
            row_dict = _row_dict(columns, row)
            act_id = get_value(row_dict, "activity_id")
            activity_name = get_value(row_dict, "activity")
            frequency = get_value(row_dict, "frequency")
            
            if not act_id or not activity_name or not frequency:
                continue

            seen_activities.add(act_id)
            
            mod_id_str = get_value(row_dict, "module_id")
            module = session.query(Module).filter(Module.external_id == mod_id_str).first() if mod_id_str else None
            
            assignee_id_str = get_value(row_dict, "assignee_id")
            assignee = session.query(User).filter(User.external_id == assignee_id_str).first() if assignee_id_str else None

            record = existing_map.get(act_id)
            if not record:
                record = session.query(ActivityRecord).filter(ActivityRecord.activity == activity_name).first()
                
            email_enabled = get_value(row_dict, "email_enabled").lower() != "no"
            whatsapp_enabled = get_value(row_dict, "whatsapp_enabled").lower() != "no"

            if record:
                record.external_id = act_id
                record.activity = activity_name
                record.frequency = frequency
                record.date_value = get_value(row_dict, "date")
                record.link = get_value(row_dict, "link")
                record.status = get_value(row_dict, "status")
                record.remark = get_value(row_dict, "remark")
                record.priority = get_value(row_dict, "priority")
                record.email_enabled = email_enabled
                record.whatsapp_enabled = whatsapp_enabled
                record.linked_module_id = module.id if module else None
                record.assignee_id = assignee.id if assignee else None
                record.sort_order = index
                record.is_active = True
            else:
                record = ActivityRecord(
                    external_id=act_id,
                    activity=activity_name,
                    frequency=frequency,
                    date_value=get_value(row_dict, "date"),
                    link=get_value(row_dict, "link"),
                    status=get_value(row_dict, "status"),
                    remark=get_value(row_dict, "remark"),
                    priority=get_value(row_dict, "priority"),
                    email_enabled=email_enabled,
                    whatsapp_enabled=whatsapp_enabled,
                    linked_module_id=module.id if module else None,
                    assignee_id=assignee.id if assignee else None,
                    sort_order=index,
                    is_active=True,
                )
                session.add(record)
                existing_map[act_id] = record

        for act_id, record in existing_map.items():
            if act_id not in seen_activities:
                record.is_active = False

        session.flush()

    def _sync_settings(self, session: Session, columns: list[str], rows: list[list[Any]]):
        column_lookup = {col.strip().casefold(): col for col in columns}
        def get_value(row_dict, key): return clean_string(row_dict.get(column_lookup.get(key), ""))
        
        key_col = "config_key" if "config_key" in column_lookup else "setting"
        val_col = "config_value" if "config_value" in column_lookup else "value"
        
        if not key_col in column_lookup or not val_col in column_lookup:
            return

        for row in rows:
            row_dict = _row_dict(columns, row)
            key = get_value(row_dict, key_col)
            val = get_value(row_dict, val_col)
            if not key:
                continue
            
            setting = session.query(NotificationSetting).filter(NotificationSetting.key == key).first()
            if setting:
                setting.value = val
            else:
                setting = NotificationSetting(key=key, value=val)
                session.add(setting)
        session.flush()
