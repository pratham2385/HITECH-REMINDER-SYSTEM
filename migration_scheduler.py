"""Migrate activities table for scheduler update."""

import sqlite3
import os

DB_PATH = "data/reminder_system.sqlite3" # Default path unless set otherwise

def migrate():
    print("Migrating activities table...")
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("timezone", "VARCHAR(50) NOT NULL DEFAULT 'UTC'"),
        ("send_time", "VARCHAR(5) NOT NULL DEFAULT '09:00'"),
        ("day_of_week", "VARCHAR(20)"),
        ("day_of_month", "INTEGER"),
        ("month_of_year", "INTEGER"),
        ("quarter_months", "VARCHAR(50)"),
        ("start_date", "DATETIME"),
        ("end_date", "DATETIME"),
        ("last_run_at", "DATETIME"),
        ("next_run_at", "DATETIME"),
        ("date_handling_strategy", "VARCHAR(20) NOT NULL DEFAULT 'exact'"),
        ("missed_execution_strategy", "VARCHAR(20) NOT NULL DEFAULT 'skip'"),
        ("email_subject_template", "VARCHAR(255)"),
        ("email_body_template", "TEXT")
    ]

    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE activities ADD COLUMN {col_name} {col_type};")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists")
            else:
                print(f"Error adding {col_name}: {e}")
                
    try:
        cursor.execute("CREATE INDEX ix_activities_next_run_at ON activities (next_run_at);")
        print("Created index on next_run_at")
    except sqlite3.OperationalError as e:
        if "already exists" in str(e):
            print("Index on next_run_at already exists")
        else:
            print(f"Error creating index: {e}")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
