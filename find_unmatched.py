import sys

filename = r'c:\Aka\School_Result\student_scor.py'
with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
print('Scanning for unmatched triple-single quotes:')
for idx, line in enumerate(lines, start=1):
    pos = 0
    while pos < len(line):
        i = line.find("'''", pos)
        if i < 0:
            break
        stack.append((idx, i, "open" if len(stack) % 2 == 0 else "close"))
        pos = i + 3

# Check final state
if len(stack) % 2 == 1:
    last_open = [s for s in stack if s[2] == "open"][-1]
    print(f"Unmatched open triple-quote at line {last_open[0]}, column {last_open[1]}")
    print(f"Total opens/closes in stack: {len(stack)}")
else:
    print("All triple quotes appear balanced")
    print(f"Total triple-quotes found: {len(stack)}")
