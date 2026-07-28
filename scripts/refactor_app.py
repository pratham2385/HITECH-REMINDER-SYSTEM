import re

def update_app_py():
    with open('src/web/app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update dashboard queries
    content = re.sub(
        r'modules_query = db\.query\(Module\)\s*if active_workspace:\s*activities_query = activities_query\.filter\(ActivityRecord\.collection_id == active_workspace\.id\)\s*modules_query = modules_query\.filter\(Module\.workspace_id == active_workspace\.id\)\s*activities = activities_query\.all\(\)',
        'if active_workspace:\n            activities_query = activities_query.filter(ActivityRecord.collection_id == active_workspace.id)\n        activities = activities_query.all()\n        categories = list(set(a.category for a in activities if a.category))',
        content, flags=re.MULTILINE
    )

    content = re.sub(
        r'modules = modules_query\.order_by\(Module\.name\.asc\(\)\)\.limit\(8\)\.all\(\)\s*module_count = modules_query\.count\(\)',
        'module_count = len(categories)\n        modules = sorted(categories)[:8]',
        content, flags=re.MULTILINE
    )

    # 2. Delete module routes
    # From @app.get("/modules") down to the end of module_delete
    module_routes_pattern = re.compile(r'@app\.get\("/modules".*?def module_delete[^\n]*\n(?:[ \t]+.*?\n)*[ \t]*return redirect\("/modules\?notice=Module deleted"\)\n[ \t]*finally:\n[ \t]*close_db\(db\)\n', re.MULTILINE | re.DOTALL)
    content = module_routes_pattern.sub('\n\n', content)

    # 3. Activities index: change modules to categories
    # Change: modules = db.query(Module).order_by(Module.name.asc()).all()
    # To: categories = list(set(a.category for a in rows if a.category))
    content = content.replace(
        'modules = db.query(Module).order_by(Module.name.asc()).all()',
        'categories = sorted(list(set(a.category for a in rows if a.category)))'
    )
    # Change "modules": modules -> "categories": categories
    content = content.replace('"modules": modules,', '"categories": categories,')

    # Fix module_id filter to category filter
    # if module_id and module_id != "all":
    #     try:
    #         mid = int(module_id)
    #         query = query.filter(ActivityRecord.linked_module_id == mid)
    #     except ValueError:
    #         pass
    category_filter = '''if module_id and module_id != "all":
            query = query.filter(ActivityRecord.category == module_id)'''
    content = re.sub(
        r'if module_id and module_id != "all":\s*try:\s*mid = int\(module_id\)\s*query = query\.filter\(ActivityRecord\.linked_module_id == mid\)\s*except ValueError:\s*pass',
        category_filter,
        content
    )

    # 4. Activity New / Edit:
    # Change modules = ... to fetching recipients
    content = content.replace(
        'modules = db.query(Module).order_by(Module.name.asc()).all()',
        'recipients = db.query(Recipient).filter(Recipient.workspace_id == active_collection.id).all() if active_collection else db.query(Recipient).all()'
    )
    content = content.replace('"modules": modules,', '')
    content = content.replace('"users": users,', '"users": users, "recipients": recipients,')

    # Activity create / update: replace linked_module_id with category, assignee_id with recipient_id
    content = re.sub(
        r'linked_module_id=.*?,\s*assignee_id=.*?,\s*',
        'category=form_data.get("category"),\n                    recipient_id=form_data.get("recipient_id") or None,\n                    ',
        content
    )

    with open('src/web/app.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_app_py()
    print("app.py updated successfully.")
