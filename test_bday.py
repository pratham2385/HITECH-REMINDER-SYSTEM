from datetime import datetime, timedelta, timezone
from src.config.settings import load_settings
from src.db.session import get_session_factory
from src.db.models import ActivityRecord, User
import logging

settings = load_settings()
SessionLocal = get_session_factory(settings)
db = SessionLocal()

# Ensure ratnakamble1983@gmail.com is an active and verified user
user = db.query(User).filter(User.email == 'ratnakamble1983@gmail.com').first()
if not user:
    user = User(
        username='ratna',
        hashed_password='xxx',
        email='ratnakamble1983@gmail.com',
        role='staff',
        display_name='Ratna Kamble',
        is_active=True,
        email_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

# Add BIRTHDAY activity assigned to that user
now = datetime.utcnow()
activity = db.query(ActivityRecord).filter(ActivityRecord.activity == 'BIRTHDAY').first()
if not activity:
    activity = ActivityRecord(
        activity='BIRTHDAY',
        frequency='daily',
        is_active=True,
        assigned_user_id=user.id,
        timezone='UTC',
        send_time=now.strftime('%H:%M'),
        next_run_at=now - timedelta(minutes=1) # due now
    )
    db.add(activity)
    db.commit()
else:
    activity.next_run_at = now - timedelta(minutes=1)
    activity.assigned_user_id = user.id
    activity.is_active = True
    db.commit()

print('Activity BIRTHDAY is set up and due for execution.')
