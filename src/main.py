"""Backward-compatible entry point for the daily reminder job."""

from __future__ import annotations

from src.jobs.send_daily_reminders import run



if __name__ == "__main__":
    raise SystemExit(run())
