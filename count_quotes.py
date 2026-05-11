import re
import sys
path = r'c:\Aka\School_Result\student_scor.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
stack = []
print('Scanning for unmatched triple-single quotes:')
for idx, line in enumerate(lines, start=1):
    pos = 0
    while True:
        i = line.find("'''", pos)
        if i < 0:
            break
        # when we see a triple quote, either push or pop
        if stack and stack[-1][0] == idx and stack[-1][1] == i:
            # this is unlikely, but just skip
            pass
        if not stack or stack[-1][2] != 'open':
            # treat as open
            stack.append((idx, i, 'open'))
        else:
            # close the last open
            stack.append((idx, i, 'close'))
        pos = i + 3
# now parse stack as simple toggles: every open should have a corresponding close
depth = 0
last_open_line = None
for entry in stack:
    if entry[2] == 'open':
        depth += 1
        last_open_line = entry[0]
    else:
        if depth > 0:
            depth -= 1
        else:
            print('extra close at', entry)
if depth:
    print('unmatched open starting at line', last_open_line)
else:
    print('all triple-single quotes paired, depth', depth)
