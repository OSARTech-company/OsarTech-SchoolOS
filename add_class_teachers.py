# Update school_admin_dashboard to include class_teachers

old_code = '''def school_admin_dashboard():
    if session.get('role') != 'school_admin':
        return redirect(url_for('login'))
    
    school_id = session.get('school_id')
    school = get_school(school_id)
    students = load_students(school_id)
    teachers = get_teachers(school_id)
    class_counts = get_student_count_by_class(school_id)
    
    return render_template('school_admin_dashboard.html', 
                         school=school, 
                         students=students,
                         teachers=teachers,
                         class_counts=class_counts)'''

new_code = '''def school_admin_dashboard():
    if session.get('role') != 'school_admin':
        return redirect(url_for('login'))
    
    school_id = session.get('school_id')
    school = get_school(school_id)
    students = load_students(school_id)
    teachers = get_teachers(school_id)
    class_counts = get_student_count_by_class(school_id)
    
    # Get class assignments (teacher for each class)
    with db_connection() as conn:
        c = conn.cursor()
        db_execute(c, """SELECT classname, teacher_id FROM class_assignments 
                       WHERE school_id = ?""", (school_id,))
        class_teachers = {}
        for row in c.fetchall():
            class_teachers[row[0]] = row[1]
    
    return render_template('school_admin_dashboard.html', 
                         school=school, 
                         students=students,
                         teachers=teachers,
                         class_counts=class_counts,
                         class_teachers=class_teachers)'''

with open('student_scor.py', 'r') as f:
    content = f.read()

content = content.replace(old_code, new_code)

with open('student_scor.py', 'w') as f:
    f.write(content)

print('Updated school_admin_dashboard function')
