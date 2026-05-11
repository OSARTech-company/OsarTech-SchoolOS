with open(r'c:\Aka\School_Result\student_scor.py', 'r') as f:
    lines = f.readlines()

# Simulate Python's lexer - track triple-quote pairs
in_triple_string = False
triple_string_start = None
quote_type = None

for line_num, line in enumerate(lines, 1):
    # Simple approach: count unescaped triple quotes
    i = 0
    while i < len(line):
        # Look for ''' or """
        if i + 2 < len(line):
            three_char = line[i:i+3]
            if three_char in ('"""', "'''"):
                if not in_triple_string:
                    in_triple_string = True
                    triple_string_start = line_num
                    quote_type = three_char
                elif three_char == quote_type:
                    in_triple_string = False
                    quote_type = None
                i += 3
                continue
        i += 1

if in_triple_string:
    print(f"Unclosed triple-{quote_type} string starting at line {triple_string_start}")
    print(f"File ends at line {len(lines)}")
else:
    print("All triple-quote pairs matched")
