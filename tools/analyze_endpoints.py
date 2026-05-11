import re
import json
import os
import student_scor

# collect routes
app = student_scor.app
routes = []
for r in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    methods = sorted(r.methods - {'HEAD', 'OPTIONS'})
    routes.append({'endpoint': r.endpoint, 'rule': r.rule, 'methods': methods})

# collect template url_for endpoints
template_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates')
endpoints_in_templates = set()
for root, dirs, files in os.walk(template_dir):
    for fn in files:
        if fn.endswith('.html'):
            p = os.path.join(root, fn)
            with open(p, 'r', encoding='utf-8') as f:
                txt = f.read()
            for m in re.finditer(r"url_for\('\s*([^'\)\s]+)\s*'\)", txt):
                endpoints_in_templates.add(m.group(1))
            for m in re.finditer(r'url_for\("\s*([^"\)\s]+)\s*"\)', txt):
                endpoints_in_templates.add(m.group(1))

out = {
    'routes': routes,
    'template_endpoints': sorted(endpoints_in_templates)
}
print(json.dumps(out, indent=2))
