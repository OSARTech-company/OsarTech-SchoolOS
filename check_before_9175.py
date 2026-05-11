filename = r'c:\Aka\School_Result\student_scor.py'
with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Lines 9170-9180 with triple-quotes marked:")
for idx in range(9169, 9180):
    line = lines[idx]
    count = line.count("'''")
    quoted = " <-- HAS QUOTES" if count > 0 else ""
    print(f"{idx+1:4d}: {repr(line[:100])}{quoted}")

print("\n\nNow checking backwards from 9175 to find unmatched triple-quotes:")
stack = []
for idx, line in enumerate(lines, start=1):
    pos = 0
    while pos < len(line):
        i = line.find("'''", pos)
        if i < 0:
            break
        if len(stack) % 2 == 0:
            stack.append((idx, "OPEN"))
        else:
            stack.append((idx, "CLOSE"))
        pos = i + 3
    if idx == 9175:
        break

print(f"After processing lines 1-9175:")
print(f"  Stack size: {len(stack)}")
print(f"  Stack is {'BALANCED' if len(stack) % 2 == 0 else 'UNBALANCED'}")
if len(stack) % 2 == 1:
    print(f"  Last few entries in stack:")
    for s in stack[-10:]:
        print(f"    Line {s[0]:4d}: {s[1]}")
