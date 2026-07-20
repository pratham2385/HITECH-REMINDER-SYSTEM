# Excel Import Analysis

Based on a recursive analysis of the codebase, here is the breakdown of the current Excel import implementation and a recommended structure for production.

## Current Implementation Analysis

### 1. Expected Excel Columns
The system currently uses a "duck typing" approach to determine if a sheet contains reminders. In `src/services/excel_importer.py`, the `_is_activity_like()` function checks if a sheet has columns named (case-insensitive):
*   `Activity`
*   `Frequency`
*   `Date`

If these three exist, the sheet is parsed as a reminder sheet. It also natively supports mapping the following optional columns into the database:
*   `Link`
*   `Status`
*   `Remark`

### 2. Entities in the Project
**Database Models (`src/db/models.py`)**:
*   `User`: Admin/Viewer accounts.
*   `Module`: Represents an imported Excel sheet.
*   `ModuleField`: Represents the column headers of an imported sheet.
*   `ModuleDataRecord`: Represents a single row in an imported sheet (stored as JSON).
*   `ActivityRecord`: The actual reminder object used by the scheduler.
*   `WorkbookImport` & `ImportedSheet`: Audit logs of file uploads.
*   `ReminderRun`, `EmailLog`, `WhatsAppLog`: Audit logs for dispatches.
*   `NotificationSetting`: Dynamic application settings.
*   `AuditLog`: Tracks user changes.

**Domain Models (`src/models.py`)**:
*   `Activity`: A DTO used in the scheduler representing an activity to run today.
*   `EmailContent`, `EmailSendResult`, `WhatsAppSendResult`: Network abstractions.

### 3. Dashboard Modules Implemented
The dashboard does not have hardcoded feature modules (e.g., "Accounting", "HR"). Instead, it uses a **Flexible Module System**. When an Excel sheet is imported, it dynamically creates a `Module`, generates `ModuleField` records for columns, and stores rows as JSON in `ModuleDataRecord`. If the sheet matches the `Activity/Frequency/Date` signature, it *additionally* mirrors those rows into `ActivityRecord` for the background scheduler to process.

### 4. Relationships
*   `WorkbookImport` has many `ImportedSheet` records.
*   `Module` has many `ModuleField` and `ModuleDataRecord` records.
*   `Module` has a one-to-many relationship with `ActivityRecord`.
*   `ReminderRun` has many `EmailLog` and `WhatsAppLog` records.

---

## Recommended Production Excel Structure

To maximize the dashboard's capabilities without modifying the core architecture, the client should adopt the following Excel structure.

### 1. Required Sheets
The Excel file can contain as many sheets as desired. However, to be tracked by the reminder system, sheets must be structured as "Activity Sheets". Non-activity sheets will still be imported and visible on the dashboard as data tables, but they will not generate email/WhatsApp reminders.

*   **Sheet 1**: `Daily Tasks` (Activity Sheet)
*   **Sheet 2**: `Monthly Compliance` (Activity Sheet)
*   **Sheet 3**: `Client Roster` (Non-Activity Data Sheet)

### 2. Required Columns (For Activity Sheets)
Every activity sheet **must** contain these three columns for the scheduler to recognize them:
1.  **`Activity`**: The name/description of the task (e.g., "Reconcile Bank Accounts").
2.  **`Frequency`**: Must exactly match one of the supported strings:
    *   `Daily`
    *   `Weekly`
    *   `Bi-Weekly` (or `Biweekly`)
    *   `Monthly`
    *   `Quarterly`
    *   `Yearly`
3.  **`Date`**: The trigger date constraint.
    *   For Monthly: A number (e.g., `15`, `31`) or `Last Day`.
    *   For Weekly/Bi-Weekly: A weekday string (e.g., `Monday`).
    *   For Yearly: A month name (e.g., `January`).

**Optional (Highly Recommended) Columns:**
*   **`Link`**: A URL pointing to relevant documents or portals.
*   **`Status`**: e.g., "Pending", "Completed".
*   **`Remark`**: Additional notes to append to the email body.

### 3. Primary and Foreign Keys
Currently, the system relies on the **`Activity`** column as a pseudo-primary key during upserts. 
*   **The Flaw**: If a user renames an activity in the Excel file from "Bank Recon" to "Bank Reconciliation", the importer treats it as a brand new activity and soft-deletes the old one, resetting any historical tracking or status flags in the dashboard.
*   **Recommendation**: Introduce a permanent identifier.

### 4. Required Modifications in Importer Code
If this structure goes to production, the following modifications to `src/services/excel_importer.py` are strongly advised:

1.  **Introduce an `Activity ID` Column**: 
    Modify `_import_activity_rows` to use an explicit `ID` column as the primary key rather than the `Activity` name.
2.  **Stop Hard-Deleting Fields/Records**:
    Currently, `session.query(ModuleDataRecord).filter(...).delete()` is called every time a sheet is re-imported. This destroys row-level historical continuity and causes database lock contention. It should be refactored into a soft-delete or a selective upsert mechanism.
3.  **Data Validation Warnings**:
    The importer silently ignores rows where the Frequency is misspelled (e.g., "Dairy" instead of "Daily"). It should log these as validation warnings in the `WorkbookImport` record.
