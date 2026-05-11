import re

filename = r'c:\Aka\School_Result\student_scor.py'
with open(filename, 'r', encoding='utf-8') as f:
    content = f.read()

# Use simple finditer to find all ''' occurrences
pattern = r"'''"
matches = list(re.finditer(pattern, content))
print(f"Found {len(matches)} triple-quote occurrences")

lines = content.splitlines()
line_numbers = []
for m in matches:
    # Count newlines before this match to get line number
    line_num = content[:m.start()].count('\n') + 1
    col = m.start() - content.rfind('\n', 0, m.start())
    line_numbers.append((line_num, col, content[max(0, m.start()-20):m.start()+20]))

# Check pairing
if len(line_numbers) % 2 == 1:
    print(f"\nOdd number of triple-quotes ({len(line_numbers)}), there's an unpaired one")
    print(f"\nLast 15 occurrences:")
    for i, (line, col, context) in enumerate(line_numbers[-15:], start=len(line_numbers)-14):
        print(f"  {i}. Line {line}, Col {col}")
        
# Try to find which one is unpaired by simulating parsing
stack = []
for i, (line, col, context) in enumerate(line_numbers):
    if i % 2 == 0:
        stack.append(('OPEN', line, col))
    else:
        if stack:
            stack.pop()
        else:
            stack.append(('CLOSE_UNMATCHED', line, col))

if stack:
    print(f"\nUnmatched quotes:")
    for s in stack:
        print(f"  Line {s[1]}: {s[0]}")
