<#
.SYNOPSIS
Sets up a Windows Scheduled Task to run the HITECH Email Reminder System.

.DESCRIPTION
This script registers a scheduled task that runs on system startup and restarts the FastAPI server via Uvicorn.
It also ensures the working directory is set correctly.
#>

$TaskName = "HitechReminderSystem"
$ProjectDir = (Get-Item -Path ".\").FullName
$VenvPython = "$ProjectDir\.venv\Scripts\python.exe"
$UvicornCommand = "-m uvicorn src.web.app:app --host 0.0.0.0 --port 8000"

if (-Not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment python not found at $VenvPython. Please run this script from the project root." -ForegroundColor Red
    exit 1
}

$Action = New-ScheduledTaskAction -Execute $VenvPython -Argument $UvicornCommand -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Runs the HITECH Email Reminder Dashboard and Background Scheduler"

Write-Host "Successfully registered Windows Scheduled Task: $TaskName" -ForegroundColor Green
Write-Host "The application will now start automatically when the system boots."
