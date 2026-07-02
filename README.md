# Automated Activity Reminder System

A production-ready Python reminder system that reads office activities from an Excel workbook and sends one daily Gmail reminder containing every activity due today.

The Excel workbook is the single source of truth. Add, remove, edit, reschedule, or change frequencies in `data/Accountant_TODO.xlsx`; the next run automatically uses the latest workbook content without code changes.

## Folder Structure

```text
email-reminder-system/
|-- data/
|   |-- Accountant_TODO.xlsx
|-- src/
|   |-- config/
|   |   |-- settings.py
|   |-- email/
|   |   |-- email_sender.py
|   |   |-- email_template.py
|   |-- excel/
|   |   |-- excel_reader.py
|   |-- scheduler/
|   |   |-- schedule_checker.py
|   |-- utils/
|   |   |-- helpers.py
|   |   |-- logger.py
|   |-- main.py
|   |-- models.py
|-- logs/
|   |-- email.log
|   |-- error.log
|-- tests/
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- README.md
```

## Installation

1. Install Python 3.11 or newer.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your Gmail credentials:

```env
EMAIL_ADDRESS=youraccount@gmail.com
EMAIL_APP_PASSWORD=your_16_character_app_password
RECIPIENT_EMAIL=recipient@example.com
EXCEL_PATH=
```

`EXCEL_PATH` is optional. Leave it blank to use `data/Accountant_TODO.xlsx`, or set it to an absolute path if the workbook lives elsewhere.

## Gmail App Password

Gmail SMTP requires an app password when two-step verification is enabled.

1. Open your Google Account.
2. Go to Security.
3. Enable 2-Step Verification if it is not already enabled.
4. Create an App Password for Mail.
5. Paste the generated 16-character password into `EMAIL_APP_PASSWORD`.

Do not use your normal Gmail password and do not commit `.env` to source control.

## Excel Format

The workbook must contain these columns:

- `Sr. No`
- `Activity`
- `Frequency`
- `Date`
- `Link`
- `Status`
- `Remark`

The reminder engine only requires:

- `Activity`
- `Frequency`
- `Date`

Supported frequencies:

- `Daily`: included every day.
- `Monthly`: `Date` must contain the day of month, such as `7` or `20`.
- `Quarterly`: due in January, April, July, and October when the day matches `Date`.
- `Yearly`: due when the month in `Date` matches the current month, such as `July month`, `April month`, or `December month`.

Rows with blank activities, unsupported frequencies, or invalid dates are skipped and written to the logs.

## Running The Project

```powershell
python -m src.main
```

Every execution writes to:

- `logs/email.log` for normal run events.
- `logs/error.log` for warnings, errors, and exceptions.

If no activity is due today, the program logs the result and exits without sending an email.

## Windows Task Scheduler Setup

1. Open Task Scheduler.
2. Select Create Basic Task.
3. Name it `Automated Activity Reminder System`.
4. Choose Daily and set the preferred reminder time.
5. Select Start a Program.
6. Program/script:

```text
C:\Path\To\Project\.venv\Scripts\python.exe
```

7. Add arguments:

```text
-m src.main
```

8. Start in:

```text
C:\Path\To\Project
```

9. Save the task and run it once manually to confirm logs are created and email delivery works.

## Running Tests

```powershell
python -m unittest
```

## Future Enhancements

- WhatsApp reminders
- SMS reminders
- Microsoft Teams notifications
- Slack notifications
- Dashboard
- Database-backed activity history
- Holiday calendar
- Reminder X days before due date
- Escalation emails
- Multiple recipients
- HTML email templates

