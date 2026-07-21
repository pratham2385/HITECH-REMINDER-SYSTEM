import os
from sqlalchemy import text
from src.db.session import init_database, get_engine, db_session
from src.db.models import *
from src.security import hash_password

def run():
    print("Running database migrations...")
    engine = get_engine()
    
    with engine.begin() as conn:
        try:
            # Safely attempt to add new columns to users
            # SQLite does not support IF NOT EXISTS in ALTER TABLE, so we catch the exception if they exist
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
            print("Added column 'email' to users.")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0"))
            print("Added column 'email_verified' to users.")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0"))
            print("Added column 'must_change_password' to users.")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE activities ADD COLUMN assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"))
            print("Added column 'assigned_user_id' to activities.")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE module_records ADD COLUMN assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"))
            print("Added column 'assigned_user_id' to module_records.")
        except Exception:
            pass

    print("Creating any missing tables...")
    init_database()
    
    print("Seeding default admin user...")
    with db_session() as session:
        admin_email = "admin@hitech.com"
        existing_admin = session.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            session.add(
                User(
                    username="admin_legacy",  # kept for legacy compatibility
                    email=admin_email,
                    display_name="Admin",
                    password_hash=hash_password("Admin@123"),
                    role="admin",
                    is_active=True,
                    email_verified=True,
                    must_change_password=True,
                )
            )
            print(f"Seeded {admin_email}.")

    print("Done.")

if __name__ == "__main__":
    run()
