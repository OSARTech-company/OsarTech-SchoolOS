import sys

filename = r'c:\Aka\School_Result\student_scor.py'
lines = open(filename, 'r', encoding='utf-8').read().splitlines()
for i in range(9170, 9186):
    if i < len(lines):
        print(i+1, repr(lines[i]))
