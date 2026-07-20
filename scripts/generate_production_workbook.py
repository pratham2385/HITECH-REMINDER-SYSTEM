import random
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill
from pathlib import Path

def generate_production_workbook(output_path: Path):
    wb = Workbook()
    
    # --- 1. Users ---
    ws_users = wb.active
    ws_users.title = "Users"
    ws_users.append(["User_ID", "Name", "Email", "Phone", "Role", "Department"])
    
    users = [
        ("U001", "Ravi Kumar", "ravi.k@example.com", "+919876543210", "Admin", "Finance"),
        ("U002", "Priya Sharma", "priya.s@example.com", "+919876543211", "Finance Manager", "Finance"),
        ("U003", "Amit Patel", "amit.p@example.com", "+919876543212", "Accountant", "Finance"),
        ("U004", "Sneha Reddy", "sneha.r@example.com", "+919876543213", "Accountant", "Finance"),
        ("U005", "Vikram Singh", "vikram.s@example.com", "+919876543214", "Accountant", "Finance"),
        ("U006", "Anjali Desai", "anjali.d@example.com", "+919876543215", "HR Executive", "HR"),
        ("U007", "Rahul Verma", "rahul.v@example.com", "+919876543216", "HR Executive", "HR"),
        ("U008", "Kavita Iyer", "kavita.i@example.com", "+919876543217", "Finance Manager", "Finance"),
        ("U009", "Manoj Tiwari", "manoj.t@example.com", "+919876543218", "Auditor", "Audit"),
        ("U010", "Pooja Joshi", "pooja.j@example.com", "+919876543219", "Auditor", "Audit"),
        ("U011", "Sanjay Gupta", "sanjay.g@example.com", "+919876543220", "Accountant", "Finance"),
        ("U012", "Neha Malhotra", "neha.m@example.com", "+919876543221", "Accountant", "Finance"),
        ("U013", "Karthik Nair", "karthik.n@example.com", "+919876543222", "Finance Manager", "Finance"),
        ("U014", "Simran Kaur", "simran.k@example.com", "+919876543223", "HR Executive", "HR"),
        ("U015", "Arun Jha", "arun.j@example.com", "+919876543224", "Auditor", "Audit")
    ]
    for u in users:
        ws_users.append(list(u))

    # --- 2. Modules ---
    ws_modules = wb.create_sheet(title="Modules")
    ws_modules.append(["Module_ID", "Module_Name", "Description", "Owner_ID"])
    
    modules = [
        ("M01", "GST", "Goods and Services Tax filings", "U002"),
        ("M02", "Payroll", "Salary processing and compliance", "U006"),
        ("M03", "TDS", "Tax Deducted at Source submissions", "U008"),
        ("M04", "Vendor Payments", "Accounts Payable processing", "U013"),
        ("M05", "Compliance", "Statutory compliance and filings", "U001"),
        ("M06", "Audits", "Internal and external audits", "U009"),
        ("M07", "Financial Reports", "MIS and Financial statements", "U002")
    ]
    for m in modules:
        ws_modules.append(list(m))

    # --- 3. Activities ---
    ws_activities = wb.create_sheet(title="Activities")
    # Added the specific columns requested: assigned user, module, due date, frequency, email enabled, WhatsApp enabled, priority, status.
    # Note: The system requires "Activity", "Frequency", and "Date" natively. We add the rest as extra columns.
    ws_activities.append([
        "Activity_ID", "Activity", "Module_ID", "Assignee_ID", 
        "Frequency", "Date", "Priority", "Status", 
        "Email_Enabled", "WhatsApp_Enabled", "Remark", "Link"
    ])

    activity_templates = [
        # GST (Monthly, Yearly)
        ("GSTR-1 Filing", "M01", "Monthly", "11", "High", "GST portal filing."),
        ("GSTR-3B Filing", "M01", "Monthly", "20", "High", "GST portal filing."),
        ("GSTR-9 Annual Return", "M01", "Yearly", "December", "Medium", "Annual reconciliation."),
        ("GST Recon with 2A/2B", "M01", "Monthly", "14", "Medium", "Reconciliation."),
        ("GST Payment", "M01", "Monthly", "20", "Critical", "Tax payment to government."),
        # Payroll (Monthly)
        ("Salary Processing", "M02", "Monthly", "Last Day", "Critical", "Process bank transfers."),
        ("PF Payment", "M02", "Monthly", "15", "High", "Provident fund remittance."),
        ("ESIC Payment", "M02", "Monthly", "15", "High", "Employee State Insurance."),
        ("PT Payment", "M02", "Monthly", "20", "Medium", "Professional Tax."),
        ("Issue Payslips", "M02", "Monthly", "1", "Low", "Distribute to employees."),
        ("Quarterly TDS Return (Form 24Q)", "M02", "Quarterly", "31", "High", "Payroll TDS."),
        # TDS (Monthly, Quarterly)
        ("TDS Payment (Non-Salary)", "M03", "Monthly", "7", "Critical", "Deposit to bank."),
        ("Quarterly TDS Return (Form 26Q)", "M03", "Quarterly", "31", "High", "Non-salary TDS return."),
        ("Issue Form 16/16A", "M03", "Yearly", "June", "Medium", "Issue to vendors/employees."),
        ("TDS Reconciliation", "M03", "Monthly", "10", "Medium", "Reconcile with books."),
        ("Collect Lower Deduction Certs", "M03", "Yearly", "April", "Low", "From vendors."),
        # Vendor Payments (Weekly, Bi-Weekly)
        ("Vendor Payment Run (A-M)", "M04", "Bi-Weekly", "Tuesday", "High", "Clear approved invoices."),
        ("Vendor Payment Run (N-Z)", "M04", "Bi-Weekly", "Thursday", "High", "Clear approved invoices."),
        ("Urgent Vendor Payments", "M04", "Weekly", "Friday", "Critical", "Ad-hoc urgent clearing."),
        ("Vendor Ageing Report", "M04", "Monthly", "5", "Medium", "Review payables."),
        ("Reconcile Vendor SOA", "M04", "Monthly", "15", "Medium", "Statement of accounts."),
        # Compliance (Monthly, Yearly)
        ("Income Tax Filing (Company)", "M05", "Yearly", "October", "Critical", "ITR-6 Filing."),
        ("Advance Tax Payment (Q1)", "M05", "Yearly", "June", "High", "15th June."),
        ("Advance Tax Payment (Q2)", "M05", "Yearly", "September", "High", "15th September."),
        ("Advance Tax Payment (Q3)", "M05", "Yearly", "December", "High", "15th December."),
        ("Advance Tax Payment (Q4)", "M05", "Yearly", "March", "High", "15th March."),
        ("MCA Annual Return (AOC-4)", "M05", "Yearly", "October", "High", "RoC Filing."),
        ("MCA Annual Return (MGT-7)", "M05", "Yearly", "November", "High", "RoC Filing."),
        ("Director KYC (DIR-3)", "M05", "Yearly", "September", "Medium", "MCA Portal."),
        ("Trade License Renewal", "M05", "Yearly", "March", "High", "Local municipality."),
        # Audits (Quarterly, Yearly)
        ("Quarterly Internal Audit", "M06", "Quarterly", "15", "High", "Internal checks."),
        ("Statutory Audit Prep", "M06", "Yearly", "May", "High", "Prepare schedules."),
        ("Tax Audit Prep", "M06", "Yearly", "August", "High", "Form 3CD prep."),
        ("Inventory Physical Verification", "M06", "Yearly", "March", "Medium", "Count stock."),
        ("Fixed Asset Verification", "M06", "Yearly", "March", "Medium", "Tagging and count."),
        ("Review Audit Findings", "M06", "Quarterly", "30", "Medium", "Management review."),
        # Financial Reports (Daily, Weekly, Monthly)
        ("Daily Bank Reconciliation", "M07", "Daily", "", "High", "Match bank lines."),
        ("Daily Cash Flow Report", "M07", "Daily", "", "Medium", "Morning cash position."),
        ("Weekly Sales Report", "M07", "Weekly", "Monday", "Medium", "Sales review."),
        ("Weekly Collections Report", "M07", "Weekly", "Wednesday", "Medium", "AR Review."),
        ("Monthly MIS Preparation", "M07", "Monthly", "10", "High", "Profit & Loss, Balance Sheet."),
        ("Monthly Board Pack", "M07", "Monthly", "15", "High", "Deck for directors."),
        ("Budget vs Actuals Review", "M07", "Monthly", "12", "Medium", "Variance analysis."),
        ("Intercompany Reconciliation", "M07", "Monthly", "8", "Medium", "Match group books."),
        ("Update Rolling Forecast", "M07", "Monthly", "20", "Medium", "Financial projection."),
        ("Month-End Provisions", "M07", "Monthly", "2", "High", "Accruals entry."),
        ("Depreciation Run", "M07", "Monthly", "3", "Low", "ERP automated run."),
        ("Review Suspense Accounts", "M07", "Weekly", "Friday", "Medium", "Clear pending entries."),
        ("Credit Card Reconciliation", "M07", "Monthly", "5", "Medium", "Corporate cards."),
        ("Petty Cash Replenishment", "M07", "Weekly", "Friday", "Low", "Physical cash count.")
    ]

    for i, act in enumerate(activity_templates, start=1):
        act_name, mod_id, freq, date_val, priority, remark = act
        # Assign user based on module matching
        assignee = random.choice(users)[0]
        if mod_id == "M02":
            assignee = random.choice(["U006", "U007", "U014"]) # HR
        elif mod_id == "M06":
            assignee = random.choice(["U009", "U010", "U015"]) # Audit
        else:
            assignee = random.choice(["U002", "U003", "U004", "U005", "U008", "U011", "U012", "U013"]) # Finance

        email_enabled = "Yes"
        whatsapp_enabled = random.choice(["Yes", "No"]) if priority in ["Medium", "Low"] else "Yes"
        status = random.choice(["Pending", "In Progress", "Completed"])

        row = [
            f"ACT-{i:03d}", act_name, mod_id, assignee,
            freq, date_val, priority, status,
            email_enabled, whatsapp_enabled, remark, "https://erp.hitech.local"
        ]
        ws_activities.append(row)

    # Adding Data Validation to Activities
    dv_freq = DataValidation(type="list", formula1='"Daily,Weekly,Bi-Weekly,Monthly,Quarterly,Yearly"', allow_blank=False)
    ws_activities.add_data_validation(dv_freq)
    dv_freq.add("E2:E100")
    
    dv_status = DataValidation(type="list", formula1='"Pending,In Progress,Completed,Blocked"', allow_blank=True)
    ws_activities.add_data_validation(dv_status)
    dv_status.add("H2:H100")
    
    dv_yesno = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
    ws_activities.add_data_validation(dv_yesno)
    dv_yesno.add("I2:J100")
    
    dv_priority = DataValidation(type="list", formula1='"Critical,High,Medium,Low"', allow_blank=False)
    ws_activities.add_data_validation(dv_priority)
    dv_priority.add("G2:G100")

    # --- 4. Reminder_Config ---
    ws_config = wb.create_sheet(title="Reminder_Config")
    ws_config.append(["Config_Key", "Config_Value"])
    ws_config.append(["Default_Dispatch_Time", "08:00 AM"])
    ws_config.append(["Max_Retries", "3"])
    ws_config.append(["Timezone", "Asia/Kolkata"])
    ws_config.append(["Company_Name", "HITECH Industries"])

    # --- 5. Email_Settings ---
    ws_email = wb.create_sheet(title="Email_Settings")
    ws_email.append(["Setting", "Value"])
    ws_email.append(["SMTP_Server", "smtp.gmail.com"])
    ws_email.append(["SMTP_Port", "587"])
    ws_email.append(["Sender_Email", "reminders@hitech.local"])
    ws_email.append(["Daily_Digest", "Yes"])

    # --- 6. WhatsApp_Settings ---
    ws_wa = wb.create_sheet(title="WhatsApp_Settings")
    ws_wa.append(["Setting", "Value"])
    ws_wa.append(["Template_Name", "daily_activity_reminder"])
    ws_wa.append(["Language_Code", "en_US"])
    ws_wa.append(["API_Version", "v20.0"])

    # --- 7. Reminder_History ---
    ws_history = wb.create_sheet(title="Reminder_History")
    ws_history.append(["Run_ID", "Run_Date", "Activities_Sent", "Email_Status", "WhatsApp_Status", "Errors"])
    
    # Generate 14 days of history
    start_date = datetime.now() - timedelta(days=14)
    for i in range(14):
        run_date = start_date + timedelta(days=i)
        activities_sent = random.randint(2, 10)
        # Occasional failure
        email_status = "Sent" if random.random() > 0.05 else "Failed"
        whatsapp_status = "Sent" if random.random() > 0.1 else "Failed"
        error = "Timeout" if email_status == "Failed" or whatsapp_status == "Failed" else ""
        
        ws_history.append([
            f"RUN-{8000+i}", run_date.strftime("%Y-%m-%d"), 
            activities_sent, email_status, whatsapp_status, error
        ])

    # --- 8. Import_Logs ---
    ws_logs = wb.create_sheet(title="Import_Logs")
    ws_logs.append(["Import_ID", "Timestamp", "Sheet_Count", "Row_Count", "Status"])
    
    start_time = datetime.now() - timedelta(days=14)
    for i in range(10):
        ts = start_time + timedelta(days=i, hours=random.randint(1, 10))
        ws_logs.append([
            f"IMP-{1000+i}", ts.strftime("%Y-%m-%d %H:%M:%S"),
            "8", "85", "Success"
        ])

    # Styling headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    
    for sheet in wb.worksheets:
        for cell in sheet[1]:
            cell.font = header_font
            cell.fill = header_fill

        # Auto-adjust column widths
        for col in sheet.columns:
            max_length = 0
            column = col[0].column_letter # Get the column name
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            sheet.column_dimensions[column].width = min(adjusted_width, 50)

    wb.save(output_path)
    print(f"Workbook successfully generated at {output_path}")

if __name__ == "__main__":
    output = Path("data/Production_Reminders.xlsx")
    output.parent.mkdir(exist_ok=True)
    generate_production_workbook(output)
