import os
from sqlalchemy import text
from src.db.session import db_session
from src.db.models import Module, ActivityRecord, User

def seed():
    with db_session() as session:
        # Check if modules already exist
        if session.query(Module).count() > 0:
            print("Modules already exist. Skipping seed.")
            return

        print("Seeding sample modules and activities...")
        modules_data = [
            "GST Returns",
            "Payroll Processing",
            "TDS Submission",
            "Vendor Payments",
            "Compliance & Audits"
        ]

        module_map = {}
        for m_name in modules_data:
            module = Module(name=m_name, description=f"Module for {m_name}")
            session.add(module)
            module_map[m_name] = module
        
        session.flush()

        activities_data = [
            ("GSTR-1 Filing", "Monthly", "11", "GST Returns"),
            ("GSTR-3B Filing", "Monthly", "20", "GST Returns"),
            ("Salary Processing", "Monthly", "1", "Payroll Processing"),
            ("PF Payment", "Monthly", "15", "Payroll Processing"),
            ("TDS Payment", "Monthly", "7", "TDS Submission"),
            ("Quarterly TDS Return", "Quarterly", "15", "TDS Submission"),
            ("Vendor Payment Run", "Weekly", "Friday", "Vendor Payments"),
            ("Annual Audit", "Yearly", "March 31", "Compliance & Audits")
        ]

        for act, freq, date_val, m_name in activities_data:
            session.add(
                ActivityRecord(
                    activity=act,
                    frequency=freq,
                    date_value=date_val,
                    linked_module_id=module_map[m_name].id,
                    
                    
                    is_active=True
                )
            )
        
        session.commit()
        print("Successfully seeded sample data.")

if __name__ == "__main__":
    seed()
