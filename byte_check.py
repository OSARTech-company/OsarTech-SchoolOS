with open(r'c:\Aka\School_Result\student_scor.py', 'rb') as f:
    content = f.read()

# Search for ''' byte sequences
triple_single = b"'''"
triple_double = b'"""'

single_count = content.count(triple_single)
double_count = content.count(triple_double)

print(f"Triple-single quotes ('''): {single_count}")
print(f"Triple-double quotes (\"\"\"): {double_count}")
print(f"Total: {single_count + double_count}")

# Check if balanced
if single_count % 2 == 1:
    print(f"\nWARNING: Odd number of triple-single quotes")
    # Find last one
    idx = content.rfind(triple_single)
    line_num = content[:idx].count(b'\n') + 1
    print(f"Last one at line {line_num}")

if double_count % 2 == 1:
    print(f"\nWARNING: Odd number of triple-double quotes")
    # Find last one
    idx = content.rfind(triple_double)
    line_num = content[:idx].count(b'\n') + 1
    print(f"Last one at line {line_num}")
