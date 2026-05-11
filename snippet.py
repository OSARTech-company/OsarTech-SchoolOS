def test():
    db_execute(
        c,
        '''INSERT INTO result_publications
           (school_id, classname, term, academic_year, teacher_id, teacher_name, principal_name, is_published, published_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(school_id, classname, term, academic_year) DO UPDATE SET
             teacher_id = excluded.teacher_id,
             teacher_name = excluded.teacher_name,
             principal_name = excluded.principal_name,
             is_published = excluded.is_published,
             published_at = excluded.published_at,
             updated_at = CURRENT_TIMESTAMP''',
        (school_id, classname, current_term, current_year or '', teacher_id, teacher_name, principal_name, 0, None),
    )
    db_execute(
        c,
        '''INSERT INTO result_publications
           (school_id, classname, term, academic_year, teacher_id, teacher_name, principal_name, is_published, published_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(school_id, classname, term, academic_year) DO UPDATE SET
             teacher_id = excluded.teacher_id,
             teacher_name = excluded.teacher_name,
             principal_name = excluded.principal_name,
             is_published = excluded.is_published,
             published_at = excluded.published_at,
             updated_at = CURRENT_TIMESTAMP''',
        (school_id, classname, current_term, current_year or '', teacher_id, teacher_name, principal_name, 0, None),
    )
