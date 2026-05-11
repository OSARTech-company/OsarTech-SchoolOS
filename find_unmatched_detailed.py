import sys

filename = r'c:\Aka\School_Result\student_scor.py'
with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
print('Scanning for unmatched triple-single quotes, tracking all:')
for idx, line in enumerate(lines, start=1):
    pos = 0
    while pos < len(line):
        i = line.find("'''", pos)
        if i < 0:
            break
        if len(stack) % 2 == 0:
            stack.append((idx, i, "OPEN"))
        else:
            stack.append((idx, i, "CLOSE"))
        if len(stack) <= 10 or len(stack) >= 308:  # Show first 10 and last few
            print(f"  {len(stack):3d}. Line {idx:5d}, Col {i:3d}: {stack[-1][2]}")
        pos = i + 3

print("\n...")
print(f"\nTotal: {len(stack)} triple-quotes")
if len(stack) % 2 == 1:
    # Find which one is unmatched
    opens = [s for s in stack if s[2] == "OPEN"]
    closes = [s for s in stack if s[2] == "CLOSE"]
    print(f"Opening quotes: {len(opens)}, Closing quotes: {len(closes)}")
    last_unmatched_open = opens[-1] if len(opens) > len(closes) else None
    if last_unmatched_open:
        print(f"\nLast unmatched OPEN at line {last_unmatched_open[0]}, col {last_unmatched_open[1]}")
