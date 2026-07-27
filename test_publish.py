import sys
from student_scor import app
import traceback

def test_publish():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        # We need a real school and user from the DB
        import psycopg2
        from student_scor import db_connection, db_execute
        
        with db_connection() as conn:
            c = conn.cursor()
            db_execute(c, "SELECT school_id FROM schools LIMIT 1")
            school_row = c.fetchone()
            if not school_row:
                print("No school found")
                return
            school_id = school_row[0]
            
            db_execute(c, "SELECT admin_id FROM school_admins WHERE school_id = ?", (school_id,))
            admin_row = c.fetchone()
            admin_id = admin_row[0] if admin_row else 'test_admin'
            
        print(f"Testing with school_id={school_id}, admin_id={admin_id}")
        
        with client.session_transaction() as sess:
            sess['role'] = 'school_admin'
            sess['school_id'] = school_id
            sess['user_id'] = admin_id
            
        try:
            resp = client.get('/school_admin_publish_results')
            print(f"GET /school_admin_publish_results -> {resp.status_code}")
            
            resp2 = client.post('/school_admin_publish_results_direct', data={
                'classname': 'JSS 1',
                'term': 'First Term'
            })
            print(f"POST /school_admin_publish_results_direct -> {resp2.status_code}")
            
        except Exception as e:
            traceback.print_exc()

if __name__ == '__main__':
    test_publish()
