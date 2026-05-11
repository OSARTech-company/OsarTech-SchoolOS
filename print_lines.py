path = r'c:\Aka\School_Result\student_scor.py'
with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, start=1):
        if 8075 <= i <= 8115:
            print(f"{i}: {line.rstrip()}")
