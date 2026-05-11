from flask import url_for
from student_scor import app

with app.app_context():
    try:
        url = url_for('school_admin_add_students_by_class', **{'class': 'JSS1'})
        print(f"Generated URL: {url}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
