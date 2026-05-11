import tokenize
from io import BytesIO

path = r'c:\Aka\School_Result\student_scor.py'
with open(path, 'rb') as f:
    data = f.read()

try:
    for tok in tokenize.tokenize(BytesIO(data).readline):
        print(tok.type, tokenize.tok_name[tok.type], repr(tok.string), tok.start, tok.end)
except tokenize.TokenError as e:
    print('TokenError', e)
    print('Args', e.args)
