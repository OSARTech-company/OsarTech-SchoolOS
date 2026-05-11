import ast
import sys

filename = r'c:\Aka\School_Result\student_scor.py'
try:
    with open(filename, 'r', encoding='utf-8') as f:
        code = f.read()
    ast.parse(code)
    print("File parses successfully!")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
    print(f"  At line {e.lineno}: {e.text}")
    print(f"  Offset {e.offset}")
    print(f"  Message: {e.msg}")
    
    # Try to show context
    lines = code.splitlines()
    if e.lineno:
        start = max(0, e.lineno - 5)
        end = min(len(lines), e.lineno + 5)
        print(f"\nContext (lines {start+1}-{end}):")
        for i in range(start, end):
            marker = " >>>  " if i == e.lineno - 1 else "      "
            print(f"{marker}{i+1:5d}: {lines[i][:100]}")
