# HITECH Email Reminder System - API Documentation

The system primarily relies on server-side rendered HTML (Jinja2) for its dashboard. However, the core routes function essentially as an API for form submissions and internal actions.

## Web Endpoints (HTML Responses)

### Auth
*   **`GET /login`**: Renders the login page.
*   **`POST /login`**: Authenticates user. Requires `username` and `password` as form data.
*   **`POST /logout`**: Clears the session cookie and logs out.

### Dashboard & Core
*   **`GET /dashboard`**: Displays pending activities, upcoming activities, and system statistics.

### Activities & Modules
*   **`GET /activities`**: Lists all imported activities (paginated).
*   **`POST /activities/{activity_id}/deactivate`**: Soft-deletes an activity.
*   **`POST /activities/{activity_id}/reactivate`**: Restores an activity.
*   **`POST /activities/{activity_id}/status`**: Updates activity status to 'Done' or clears it. Requires `status` (string).
*   **`GET /modules`**: Lists all registered modules.

### Excel Imports
*   **`GET /imports`**: Lists historical workbook imports.
*   **`GET /imports/new`**: Renders the manual file upload form.
*   **`POST /imports/new`**: Uploads and parses an Excel file. Expects `file` (UploadFile).

### Reminders & Previews
*   **`GET /reminders/preview`**: Renders a preview of what will be sent today (or on an optionally provided `preview_date`).
*   **`POST /reminders/send-test-email`**: Triggers a test email to the configured recipient.
*   **`POST /reminders/send-test-whatsapp`**: Triggers a test WhatsApp message.

### Settings
*   **`GET /settings/email`**: Displays Email configuration form.
*   **`POST /settings/email`**: Saves Email configuration.
*   **`GET /settings/whatsapp`**: Displays WhatsApp configuration form.
*   **`POST /settings/whatsapp`**: Saves WhatsApp configuration.

### User Management
*   **`GET /users`**: Lists all active users.
*   **`GET /users/new`**: Renders user creation form.
*   **`POST /users/new`**: Creates a new user.
*   **`GET /users/{user_id}/edit`**: Renders user editing form.
*   **`POST /users/{user_id}/edit`**: Updates user details.
*   **`POST /users/{user_id}/delete`**: Soft-deletes a user account.
