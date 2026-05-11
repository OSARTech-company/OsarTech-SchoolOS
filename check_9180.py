filename = r'c:\Aka\School_Result\student_scor.py'
with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

line_9180 = lines[9179]  # 0-indexed
print("Line 9180:")
print(repr(line_9180))
print("\nSearching for ''' in this line:")
pos = 0
while pos < len(line_9180):
    i = line_9180.find("'''", pos)
    if i < 0:
        break
    print(f"  Found at column {i}: {repr(line_9180[max(0,i-5):i+8])}")
    pos = i + 3
