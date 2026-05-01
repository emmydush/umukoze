import os
import re

tpl_dir = r"e:\Umukozi\templates"

# Regex to match <aside class="sidebar" ...> ... </aside>
aside_pattern = re.compile(r'<aside\s+class="sidebar"[^>]*>.*?</aside>', re.DOTALL)

for filename in os.listdir(tpl_dir):
    if not filename.endswith('.html'): continue
    filepath = os.path.join(tpl_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '<aside class="sidebar"' not in content:
        continue

    # Determine type of sidebar
    if filename.startswith('worker_'):
        sidebar_name = 'worker_sidebar.html'
    elif filename.startswith('employer_'):
        sidebar_name = 'employer_sidebar.html'
    elif filename.startswith('admin_'):
        sidebar_name = 'admin_sidebar.html'
    else:
        if 'worker.' in content or 'worker_' in content:
            sidebar_name = 'worker_sidebar.html'
        elif 'employer.' in content or 'employer_' in content:
            sidebar_name = 'employer_sidebar.html'
        else:
            sidebar_name = 'admin_sidebar.html'

    new_content = aside_pattern.sub(f"{{% include 'includes/{sidebar_name}' %}}", content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
print("Updated all sidebars!")
