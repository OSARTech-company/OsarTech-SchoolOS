import sqlite3

def sync_comments():
    try:
        from student_scor import db_connection, db_execute, get_schools
    except ImportError as e:
        print("ImportError:", e)
        return

    try:
        with db_connection(commit=True) as conn:
            c = conn.cursor()
            
            schools = get_schools()
            school_years = {str(k): v.get('academic_year', '') for k, v in schools.items()}

            from student_scor import students_has_teacher_comment_column, students_has_principal_comment_column
            has_teacher = students_has_teacher_comment_column()
            has_principal = students_has_principal_comment_column()
            
            if not has_teacher and not has_principal:
                print("No comment columns in students table.")
                return

            cols = "school_id, student_id, term"
            if has_teacher:
                cols += ", teacher_comment"
            else:
                cols += ", '' as teacher_comment"
            if has_principal:
                cols += ", principal_comment"
            else:
                cols += ", '' as principal_comment"
                
            query = f"SELECT {cols} FROM students WHERE (teacher_comment IS NOT NULL AND teacher_comment != '') OR (principal_comment IS NOT NULL AND principal_comment != '')"
            db_execute(c, query)
            students = c.fetchall()
            
            if not students:
                print("No students with comments found.")
                return
                
            count = 0
            print(f"Found {len(students)} student(s) with comments to sync...")
            for row in students:
                school_id, student_id, term, teacher_comment, principal_comment = row
                academic_year = school_years.get(str(school_id), '')
                
                update_q = """
                    UPDATE published_student_results 
                    SET teacher_comment = COALESCE(NULLIF(?, ''), teacher_comment),
                        principal_comment = COALESCE(NULLIF(?, ''), principal_comment)
                    WHERE school_id = ? AND student_id = ? AND term = ? AND COALESCE(academic_year, '') = ?
                """
                db_execute(c, update_q, (teacher_comment, principal_comment, school_id, student_id, term, academic_year))
                if c.rowcount > 0:
                    count += c.rowcount
            
            print(f"Successfully synced {count} published results with missing comments from the students table!")
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    sync_comments()
