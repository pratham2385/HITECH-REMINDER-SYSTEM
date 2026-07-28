def delete_module_routes():
    with open('src/web/app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    for line in lines:
        if line.startswith('@app.get("/modules"'):
            skip = True
        elif line.startswith('@app.get("/imports"'):
            skip = False
        
        if not skip:
            new_lines.append(line)

    with open('src/web/app.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Deleted module routes.")

if __name__ == "__main__":
    delete_module_routes()
