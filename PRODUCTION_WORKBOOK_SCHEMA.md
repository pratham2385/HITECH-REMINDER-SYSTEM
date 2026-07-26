# Production Workbook Schema & Data Dictionary

This document outlines the structure of the new production-ready Excel workbook for the HITECH Email Reminder System. 

> [!WARNING]
> **Architectural Note on System Alignment**
> The current HITECH architecture uses a SQLite database to manage Users, Settings, and Logs, utilizing the Excel file strictly for ingesting **Modules** and **Activities**. 
> While this workbook includes sheets for `Users`, `Reminder_Config`, `Email_Settings`, `WhatsApp_Settings`, `Reminder_History`, and `Import_Logs` as requested, the current `ExcelImportService` will ingest them as standard data modules. They will not override the system's actual configuration or user accounts unless we modify the source code to sync these specific sheets into the backend models.

## 1. Sheet Relationships

*   **Modules** (1) -> (Many) **Activities**: The Modules sheet defines logical groupings (e.g., "Tax Compliance", "Payroll"), and the Activities sheet contains the actual tasks, referencing the Module they belong to.
*   **Users** (Many) -> (Many) **Activities**: Users can be assigned to specific activities.
*   **Reminder_Config** (1) -> (1) **Email/WhatsApp_Settings**: Global configurations referencing specific transport settings.

## 2. Validation Rules
*   **Frequency**: Must be restricted to `Daily`, `Weekly`, `Bi-Weekly`, `Monthly`, `Quarterly`, `Yearly`.
*   **Date**: 
    *   Weekly/Bi-Weekly: Must be a valid weekday (`Monday`, `Tuesday`, etc.).
    *   Monthly: Must be a day number (`1-31`) or `Last Day`.
    *   Yearly: Must be a valid month (`January`, `February`, etc.).
*   **Status**: Restricted to `Pending`, `In Progress`, `Completed`, `Blocked`.

## 3. Data Dictionary

### Sheet: Users
*Reference list of personnel.*
*   **User_ID**: Unique identifier.
*   **Name**: Full name.
*   **Email**: Contact email address.
*   **Phone**: WhatsApp contact number.
*   **Role**: `Admin`, `Staff`, or `Viewer`.

### Sheet: Modules
*Logical groups for activities.*
*   **Module_ID**: Unique identifier.
*   **Module_Name**: Name of the grouping (e.g., "Corporate Tax").
*   **Description**: Details about the module.

### Sheet: Activities (⚠️ Primary Engine Sheet)
*This sheet contains the core reminders. The system currently looks for `Activity`, `Frequency`, and `Date`.*
*   **Activity_ID**: Unique permanent identifier for the task.
*   **Activity**: Name of the task (Required).
*   **Frequency**: Recurrence pattern (Required).
*   **Date**: Trigger condition (Required).
*   **Module_ID**: Foreign key to the Modules sheet.
*   **Assignee_ID**: Foreign key to the Users sheet.
*   **Link**: URL to external resources.
*   **Status**: Current status of the activity.
*   **Remark**: Additional contextual notes.

### Sheet: Reminder_Config
*Global orchestration settings.*
*   **Config_Key**: e.g., `Default_Time`, `Max_Retries`.
*   **Config_Value**: Value for the key.

### Sheet: Email_Settings
*SMTP configuration reference.*
*   **Setting**: e.g., `SMTP_Server`, `SMTP_Port`, `Sender_Email`.
*   **Value**: Actual configuration value.

### Sheet: WhatsApp_Settings
*Meta Graph API configuration reference.*
*   **Setting**: e.g., `Template_Name`, `Language_Code`.
*   **Value**: Actual configuration value.

### Sheet: Reminder_History
*Offline export/mirror of dispatches.*
*   **Run_ID**: Identifier for the dispatch run.
*   **Run_Date**: Date the run executed.
*   **Activities_Sent**: Count of reminders dispatched.
*   **Email_Status**: `Sent` or `Failed`.
*   **WhatsApp_Status**: `Sent` or `Failed`.

### Sheet: Import_Logs
*Offline export/mirror of file imports.*
*   **Import_ID**: Unique identifier.
*   **Timestamp**: Date and time of import.
*   **Sheet_Count**: Number of sheets imported.
*   **Row_Count**: Total rows imported.
*   **Status**: `Success` or `Failed`.
