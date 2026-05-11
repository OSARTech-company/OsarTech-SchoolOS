import tokenize
import io

filename = r'c:\Aka\School_Result\student_scor.py'
with open(filename, 'rb') as f:
    tokens = tokenize.tokenize(f.readline)
    for tok in tokens:
        if tok.type == tokenize.STRING:
            # print repr to see delimiters
            print(f"LINE {tok.start[0]} col {tok.start[1]}: {repr(tok.string)[:80]}...")
