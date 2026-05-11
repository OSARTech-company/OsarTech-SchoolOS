import tokenize
import io

filename = r'c:\Aka\School_Result\student_scor.py'
with open(filename, 'rb') as f:
    try:
        tokens = list(tokenize.tokenize(f.readline))
        print("File tokenized successfully (no syntax errors)")
    except tokenize.TokenError as e:
        print(f"Tokenize error: {e}")
        print(f"Error args: {e.args}")
