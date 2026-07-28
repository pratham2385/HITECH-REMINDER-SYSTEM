import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.session import get_session_factory, init_database
from src.config.settings import load_settings
from src.db.models import TaskCollection, ActivityRecord
from datetime import datetime

def run_migration():
    settings = load_settings()
    init_database(settings)
    
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        # Create Default Collection if not exists
        default_collection = db.query(TaskCollection).filter_by(name="Default Collection").first()
        
        if not default_collection:
            print("Creating 'Default Collection'...")
            default_collection = TaskCollection(
                name="Default Collection",
                description="Auto-generated default collection for existing activities.",
                import_date=datetime.utcnow(),
                is_active=True
            )
            db.add(default_collection)
            db.commit()
            db.refresh(default_collection)
        
        # Update existing activities
        unassigned_activities = db.query(ActivityRecord).filter(ActivityRecord.collection_id == None).all()
        count = len(unassigned_activities)
        if count > 0:
            print(f"Assigning {count} activities to 'Default Collection'...")
            for activity in unassigned_activities:
                activity.collection_id = default_collection.id
            db.commit()
            print(f"Migration completed successfully. Updated {count} activities.")
        else:
            print("No unassigned activities found. Migration already applied.")

if __name__ == "__main__":
    run_migration()
