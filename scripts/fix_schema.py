import sqlite3
import os

db_path = os.path.join("data", "reminder_system.sqlite3")

def fix_schema():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(activities)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "category" not in columns:
        cursor.execute("ALTER TABLE activities ADD COLUMN category VARCHAR(255);")
        print("Added category to activities.")

    cursor.execute("PRAGMA table_info(recipients)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "workspace_id" not in columns:
        cursor.execute("ALTER TABLE recipients ADD COLUMN workspace_id INTEGER REFERENCES task_collections(id);")
        print("Added workspace_id to recipients.")

    conn.commit()
    conn.close()
    print("Schema updated successfully.")

if __name__ == "__main__":
    fix_schema()
