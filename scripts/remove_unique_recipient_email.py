import sqlite3
import os

db_path = os.path.join("data", "reminder_system.sqlite3")

def fix_recipients_table():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Rename old table
    cursor.execute("ALTER TABLE recipients RENAME TO _recipients_old;")
    
    # 2. Create new table without UNIQUE constraint on email
    cursor.execute("""
    CREATE TABLE recipients (
        id INTEGER NOT NULL, 
        email VARCHAR(255) NOT NULL, 
        name VARCHAR(255), 
        workspace_id INTEGER, 
        created_at DATETIME NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(workspace_id) REFERENCES task_collections (id) ON DELETE CASCADE
    );
    """)

    # 3. Create indices
    cursor.execute("CREATE INDEX ix_recipients_email ON recipients (email);")

    # 4. Copy data
    cursor.execute("""
    INSERT INTO recipients (id, email, name, workspace_id, created_at)
    SELECT id, email, name, workspace_id, created_at FROM _recipients_old;
    """)

    # 5. Drop old table
    cursor.execute("DROP TABLE _recipients_old;")

    conn.commit()
    conn.close()
    print("Dropped unique constraint on recipients.email successfully.")

if __name__ == "__main__":
    fix_recipients_table()
