Testing Guide

The HITECH Email Reminder System uses `pytest` for unit testing the core scheduling and synchronization logic.

## Running Tests

1. Ensure your virtual environment is activated and dependencies are installed.
2. Run the test suite:
   ```bash
   pytest
   ```

## Test Coverage

Currently, tests cover the following domains:

- **Scheduling (`test_scheduler.py`)**: Validates the `ScheduleChecker` class handling of:
  - Daily recurrences.
  - Weekly and Bi-weekly weekday parsing.
  - Monthly exact match recurrences.
  - Monthly overflow handling (e.g. mapping the 31st to the 28th of February).
  - Monthly "End of Month" edge cases.

## Manual Verification

If you are developing locally, you can verify integrations manually using the Dashboard:

1. **Email/WhatsApp Dispatch**: Navigate to `Dashboard > Reminder Preview` and click the `Test Email` or `Test WhatsApp` buttons to manually trigger the API calls and inspect the payloads.
2. **Auto-Import Polling**: Place a new `.xlsx` file into the `data/` directory. The background scheduler will detect the timestamp change and automatically initiate a sync within 5 minutes.
3. **Daily Dispatches**: Check the `logs/app.log` file to view the output of the APScheduler daily cron job (runs at 8:00 AM server time).
