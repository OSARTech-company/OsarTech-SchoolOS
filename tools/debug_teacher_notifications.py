import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from student_scor import app, teacher_notifications
from flask import session
import traceback

with app.test_request_context('/teacher/notifications'):
    # Simulate a teacher session
    session['role'] = 'teacher'
    session['school_id'] = 'demo_school'
    session['user_id'] = 'demo_teacher'
    try:
        resp = teacher_notifications()
        print('Returned type:', type(resp))
        if hasattr(resp, 'get_data'):
            print(resp.get_data(as_text=True)[:1000])
    except Exception as e:
        traceback.print_exc()
        print('\nEXCEPTION:', repr(e))
