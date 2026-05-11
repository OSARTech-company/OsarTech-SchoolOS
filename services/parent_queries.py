import json


def load_students_for_student_ids(
    *,
    db_connection,
    db_execute,
    students_has_parent_access_columns,
    school_id,
    student_ids,
):
    """Load selected students for one school keyed by student_id."""
    ids = [str(v).strip() for v in (student_ids or []) if str(v).strip()]
    if not ids:
        return {}
    has_parent_cols = students_has_parent_access_columns()
    placeholders = ','.join(['?'] * len(ids))
    with db_connection() as conn:
        c = conn.cursor()
        if has_parent_cols:
            query = (
                'SELECT student_id, firstname, date_of_birth, gender, classname, first_year_class, term, stream, '
                'number_of_subject, subjects, scores, promoted, parent_phone, parent_password_hash '
                f'FROM students WHERE school_id = ? AND student_id IN ({placeholders})'
            )
        else:
            query = (
                'SELECT student_id, firstname, date_of_birth, gender, classname, first_year_class, term, stream, '
                'number_of_subject, subjects, scores, promoted '
                f'FROM students WHERE school_id = ? AND student_id IN ({placeholders})'
            )
        params = [school_id] + ids
        db_execute(c, query, tuple(params))
        rows = c.fetchall() or []
    out = {}
    for row in rows:
        if has_parent_cols:
            student_id, firstname, date_of_birth, gender, classname, first_year_class, term, stream, number_of_subject, subjects_str, scores_str, promoted, parent_phone, parent_password_hash = row
        else:
            student_id, firstname, date_of_birth, gender, classname, first_year_class, term, stream, number_of_subject, subjects_str, scores_str, promoted = row
            parent_phone, parent_password_hash = '', ''
        out[str(student_id or '').strip()] = {
            'student_id': student_id,
            'firstname': firstname,
            'date_of_birth': (date_of_birth or '').strip(),
            'gender': (gender or '').strip(),
            'classname': classname,
            'first_year_class': first_year_class,
            'term': term,
            'stream': stream,
            'number_of_subject': number_of_subject,
            'subjects': json.loads(subjects_str) if subjects_str else [],
            'scores': json.loads(scores_str) if scores_str else {},
            'promoted': promoted,
            'parent_phone': (parent_phone or '').strip(),
            'parent_password_hash': (parent_password_hash or '').strip(),
        }
    return out


def get_published_overview_for_students(
    *,
    db_connection,
    db_execute,
    term_token_builder,
    school_id,
    student_ids,
):
    """
    Bulk-load parent dashboard data from published_student_results.
    Returns:
      {
        'terms_by_student': {student_id: [term entries...]},
        'snapshot_by_student_token': {student_id: {token: {...avg/grade/status...}}},
      }
    """
    ids = [str(v).strip() for v in (student_ids or []) if str(v).strip()]
    if not ids:
        return {'terms_by_student': {}, 'snapshot_by_student_token': {}}
    placeholders = ','.join(['?'] * len(ids))
    with db_connection() as conn:
        c = conn.cursor()
        db_execute(
            c,
            f"""SELECT student_id, COALESCE(academic_year, ''), term, COALESCE(classname, ''),
                       published_at, average_marks, grade, status
                FROM published_student_results
                WHERE school_id = ? AND student_id IN ({placeholders})
                ORDER BY student_id, published_at ASC""",
            tuple([school_id] + ids),
        )
        rows = c.fetchall() or []

    terms_by_student = {}
    seen_terms = {}
    snapshot_by_student_token = {}
    for row in rows:
        sid = str(row[0] or '').strip()
        if not sid:
            continue
        academic_year = row[1] or ''
        term = row[2] or ''
        row_classname = row[3] or ''
        token = term_token_builder(academic_year, term)
        label = f"{term} ({academic_year})" if academic_year else term
        seen = seen_terms.setdefault(sid, set())
        seen_key = (token, (row_classname or '').strip().lower())
        if seen_key not in seen:
            seen.add(seen_key)
            terms_by_student.setdefault(sid, []).append({
                'academic_year': academic_year,
                'term': term,
                'classname': row_classname,
                'token': token,
                'label': label,
            })
        try:
            avg_marks = float(row[5] or 0)
        except Exception:
            avg_marks = 0.0
        snapshot_by_student_token.setdefault(sid, {})[token] = {
            'average_marks': avg_marks,
            'Grade': row[6] or 'F',
            'Status': row[7] or 'Fail',
            'term': term,
            'academic_year': academic_year,
            'classname': row_classname,
        }
    return {
        'terms_by_student': terms_by_student,
        'snapshot_by_student_token': snapshot_by_student_token,
    }

