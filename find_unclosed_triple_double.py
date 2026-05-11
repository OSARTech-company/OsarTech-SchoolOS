import re

path = r'c:\Aka\School_Result\student_scor.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

pattern = re.compile(r'("""|\'\'\')')

found = []
for idx, line in enumerate(lines, start=1):
    for m in pattern.finditer(line):
        found.append((idx, m.group(1)))

print(f"Total triple-quote occurrences: {len(found)}")
# print some
for idx, quote in found[:50]:
    print(idx, quote)

# Now check pairing for triple-double vs triple-single separately
for quote_type in ['"""', "'''"]:
    stack = []
    for idx, qt in found:
        if qt != quote_type:
            continue
        if not stack or stack[-1][2] != 'open':
            stack.append((idx, qt, 'open'))
        else:
            stack.append((idx, qt, 'close'))
    depth = 0
    last_open = None
    for entry in stack:
        if entry[2] == 'open':
            depth += 1
            last_open = entry[0]
        else:
            if depth > 0:
                depth -= 1
    print(quote_type, "depth", depth, "last_open", last_open)

# also show unpaired when depth>0
if depth > 0:
    print("Possible unclosed", quote_type, "started at line", last_open)
