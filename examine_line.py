path = r'c:\Aka\School_Result\student_scor.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
line_num = 8106
line = lines[line_num - 1]
print(f"Line {line_num}: {line!r}")
for idx, ch in enumerate(line):
    if idx < 120:
        print(idx, ch)
