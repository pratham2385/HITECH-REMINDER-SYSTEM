# Deployment Guide

The HITECH Email Reminder System is designed for robust, production-ready deployments. You can deploy it using Docker (Recommended) or natively as a Windows Service/Scheduled Task.

## Option 1: Docker (Recommended)

Docker provides an isolated environment and manages the background scheduler automatically.

### Prerequisites
- Docker and Docker Compose installed on the host machine.

### Deployment Steps
1. Clone the repository to the host server.
2. Ensure you have created the `.env` file (copy `.env.example`).
3. Run the deployment:
   ```bash
   docker-compose up -d --build
   ```
4. The dashboard will be available at `http://<host-ip>:8000`.

### Data Persistence
The `docker-compose.yml` mounts the following volumes to the host to ensure data persists across restarts:
- `./data` -> `/app/data` (Contains the SQLite database `reminders.db` and Excel files)
- `./logs` -> `/app/logs` (Contains the rotating log files)

## Option 2: Native Windows Deployment

If deploying directly onto a Windows Server without Docker, you can use the built-in Windows Task Scheduler.

### Prerequisites
- Python 3.11+ installed.
- A virtual environment created at `.venv`.

### Deployment Steps
1. Install dependencies:
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
2. Initialize the database:
   ```powershell
   .\.venv\Scripts\python.exe migrate.py
   ```
3. Register the Scheduled Task:
   Run the provided PowerShell script as an Administrator:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows_scheduler.ps1
   ```
4. The service will now run automatically on system boot.

## Default Credentials
On the first run, the system will initialize an admin account based on your `.env` configuration (default is usually `admin` / `admin`). **Change this password immediately in the dashboard.**
