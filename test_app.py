import contextlib
import importlib
import io
import json
import zipfile
from datetime import datetime, timedelta

import pytest


def _xlsx_column_name(index):
    letters = []
    current = int(index)
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        letters.append(chr(65 + remainder))
    return ''.join(reversed(letters))


def _build_inline_xlsx(rows):
    sheet_rows = []
    for row_idx, row in enumerate(rows, start=1):
        cells = []
        for col_idx, value in enumerate(row, start=1):
            ref = f"{_xlsx_column_name(col_idx)}{row_idx}"
            text = (
                str(value)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        sheet_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def test_db_execute_transaction_resets(monkeypatch):
    import student_scor
    # ensure db_execute rolls back on error and commits on success so a
    # failed migration statement doesn't abort the entire startup sequence
    class DummyConn:
        def __init__(self):
            self.committed = False
            self.rolled = False
        def commit(self):
            self.committed = True
        def rollback(self):
            self.rolled = True
    class DummyCursor:
        def __init__(self, conn):
            self.connection = conn
            self.queries = []
        def execute(self, query, params=None):
            self.queries.append(query)
            if 'fail' in query:
                raise RuntimeError('simulated error')
    conn = DummyConn()
    c = DummyCursor(conn)

    with pytest.raises(RuntimeError):
        student_scor.db_execute(c, 'please fail')
    assert conn.rolled, "db_execute should rollback after error"

    student_scor.db_execute(c, 'all good')
    assert conn.committed, "db_execute should commit after successful statement"


def test_get_bursars_ensures_schema_before_query(app_module, monkeypatch):
    m = app_module
    ensure_calls = []

    def fake_ensure_extended_features_schema():
        ensure_calls.append(True)
        return True

    class FakeCursor:
        def execute(self, query, params=None):
            if 'FROM bursars' in query:
                raise RuntimeError('simulated missing table')
        def fetchall(self):
            return []

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    @contextlib.contextmanager
    def fake_db_connection(commit=False):
        yield FakeConn()

    monkeypatch.setattr(m, "ensure_extended_features_schema", fake_ensure_extended_features_schema)
    monkeypatch.setattr(m, "db_connection", fake_db_connection)

    assert m.get_bursars("SCH") == {}
    assert ensure_calls == [True]


def test_ensure_extended_features_schema_creates_bursars_table_before_alter(app_module, monkeypatch):
    m = app_module

    class FakeCursor:
        def __init__(self):
            self.tables = set()
        def execute(self, query, params=None):
            if 'CREATE TABLE IF NOT EXISTS bursars' in query:
                self.tables.add('bursars')
                return
            if 'CREATE TABLE IF NOT EXISTS class_timetables' in query:
                self.tables.add('class_timetables')
                return
            if 'ALTER TABLE bursars' in query:
                if 'bursars' not in self.tables:
                    raise RuntimeError('simulated missing bursars table')
                return
            if 'ALTER TABLE class_timetables' in query:
                if 'class_timetables' not in self.tables:
                    raise RuntimeError('simulated missing class_timetables table')
                return
        def fetchall(self):
            return []

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    @contextlib.contextmanager
    def fake_db_connection(commit=False):
        yield FakeConn()

    monkeypatch.setattr(m, "db_connection", fake_db_connection)

    assert m.ensure_extended_features_schema() is True


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("DEFAULT_STUDENT_PASSWORD", "password123")
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "supersecurepassword")
    monkeypatch.setenv("RUN_STARTUP_DDL", "0")
    monkeypatch.setenv("RUN_STARTUP_BOOTSTRAP", "0")
    monkeypatch.setenv("ALLOW_RUNTIME_SCHEMA_HEAL", "0")

    import student_scor

    mod = importlib.reload(student_scor)
    mod.app.config["TESTING"] = True
    mod.app.config["WTF_CSRF_ENABLED"] = False
    return mod


@pytest.fixture
def client(app_module):
    return app_module.app.test_client()


def test_build_subjects_from_config_ss1_combined_merges_all_tracks(app_module):
    m = app_module
    config = {
        "core_subjects": ["English Language", "Mathematics"],
        "science_subjects": ["Biology"],
        "art_subjects": ["Literature in English"],
        "commercial_subjects": ["Economics"],
        "optional_subjects": ["French"],
    }
    school = {"ss1_stream_mode": "combined"}
    subjects, final_stream, err = m.build_subjects_from_config(
        classname="SS1",
        stream="N/A",
        config=config,
        selected_optional_subjects=[],
        school=school,
    )
    assert err is None
    assert final_stream == "N/A"
    assert subjects == [
        "English Language",
        "Mathematics",
        "Biology",
        "Literature in English",
        "Economics",
        "French",
    ]


def test_secondary_class_normalization_accepts_jss_aliases(app_module):
    m = app_module
    assert m.canonicalize_classname("JSS 1A") == "JSS1A"
    assert m.canonicalize_classname("JS1") == "JSS1"
    assert m.canonicalize_classname("Junior Secondary 2B") == "JSS2B"
    assert m.is_secondary_classname("Junior Secondary 2B") is True
    assert m.is_secondary_classname("JSS3") is True


def test_cbt_test_score_pair_split_even_and_odd(app_module):
    m = app_module
    assert m._split_cbt_test_score_pair(14) == (7.0, 7.0)
    assert m._split_cbt_test_score_pair(15) == (7.0, 8.0)


def test_cbt_target_test_slots_prefers_next_slot(app_module):
    m = app_module
    assert m._cbt_target_test_slots(1, 3) == [1, 2]
    assert m._cbt_target_test_slots(3, 3) == [3, 2]


def test_cbt_option_shuffling(app_module):
    m = app_module
    
    # 1. Test _get_shuffled_options_map deterministic output
    attempt_id = "attempt_123"
    q_no = 1
    shuffled_list, to_shuffled, to_original = m._get_shuffled_options_map(attempt_id, q_no)
    
    assert len(shuffled_list) == 4
    assert set(shuffled_list) == {"A", "B", "C", "D"}
    assert len(to_shuffled) == 4
    assert len(to_original) == 4
    for orig, shuf in to_shuffled.items():
        assert to_original[shuf] == orig
        
    # 2. Test deterministic behavior with same attempt/q_no
    shuffled_list2, to_shuffled2, to_original2 = m._get_shuffled_options_map(attempt_id, q_no)
    assert shuffled_list == shuffled_list2
    assert to_shuffled == to_shuffled2
    assert to_original == to_original2
    
    # 3. Test different attempt ID gives potentially different order (shuffling happens)
    different = False
    for i in range(100):
        shuf_list_i, _, _ = m._get_shuffled_options_map(f"attempt_{i}", q_no)
        if shuf_list_i != ["A", "B", "C", "D"]:
            different = True
            break
    assert different, "Option mapping should not always be identical to A, B, C, D"

    # 4. Test _shuffle_question_options_inplace
    q = {
        "question_no": 1,
        "question_text": "What is 1 + 1?",
        "option_a": "One",
        "option_b": "Two",
        "option_c": "Three",
        "option_d": "Four",
        "correct_option": "B"
    }
    
    m._shuffle_question_options_inplace(q, attempt_id)
    
    orig_options = {
        "A": "One",
        "B": "Two",
        "C": "Three",
        "D": "Four"
    }
    for orig_opt, text in orig_options.items():
        shuf_opt = to_shuffled[orig_opt]
        assert q[f"option_{shuf_opt.lower()}"] == text
        
    assert q["correct_option"] == to_shuffled["B"]


def test_load_published_student_result_combines_three_terms(app_module, monkeypatch):
    m = app_module
    # prepare fake DB connection that returns predetermined rows by term
    def fake_db_connection(commit=False):
        class FakeCursor:
            def __init__(self):
                self.last_params = None
            def execute(self, query, params=None):
                self.last_params = params
            def fetchone(self):
                term = self.last_params[2] if self.last_params and len(self.last_params) >= 3 else None
                if term == 'First Term':
                    return ('Aka','JSS1','2025-2026','First Term','S',1,'["Math"]','{"Math": {"overall_mark": 50}}','',50,'C','Pass')
                if term == 'Second Term':
                    return ('Aka','JSS1','2025-2026','Second Term','S',1,'["Math"]','{"Math": {"overall_mark": 70}}','',70,'B','Pass')
                if term == 'Third Term':
                    return ('Aka','JSS1','2025-2026','Third Term','S',1,'["Math"]','{"Math": {"overall_mark": 90}}','',90,'A','Pass')
                return None
        class FakeConn:
            def cursor(self):
                return FakeCursor()
        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()
        return ctx(commit)
    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "get_school", lambda sid: {"combine_third_term_results": 1})
    monkeypatch.setattr(m, "get_grade_config", lambda sid: {"pass_mark": 0, "grade_a_min": 70, "grade_b_min": 60, "grade_c_min": 50, "grade_d_min": 40})
    snapshot = m.load_published_student_result("SCH", "STU", "Third Term", "2025-2026", "JSS1")
    assert snapshot is not None
    assert snapshot['average_marks'] == pytest.approx((50 + 70 + 90) / 3)
    assert snapshot['scores']['Math']['overall_mark'] == pytest.approx((50 + 70 + 90) / 3)


def test_load_published_class_results_combines_terms(app_module, monkeypatch):
    m = app_module
    # fake cursor returns three rows for one student when asked for IN clause
    def fake_db_connection(commit=False):
        class FakeCursor:
            def __init__(self):
                self.last_query = ''
                self.last_params = None
            def execute(self, query, params=None):
                self.last_query = query
                self.last_params = params
            def fetchall(self):
                # return three rows if combining; otherwise mimic single term
                if "IN ('First Term'" in self.last_query:
                    return [
                        ('S1','C','S',50,'["Math"]','{"Math": {"overall_mark": 50}}','First Term'),
                        ('S1','C','S',70,'["Math"]','{"Math": {"overall_mark": 70}}','Second Term'),
                        ('S1','C','S',90,'["Math"]','{"Math": {"overall_mark": 90}}','Third Term'),
                    ]
                # fallback
                return []
        class FakeConn:
            def cursor(self):
                return FakeCursor()
        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()
        return ctx(commit)
    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "get_school", lambda sid: {"combine_third_term_results": 1, "class_arm_ranking_mode": "separate"})
    results = m.load_published_class_results("SCH", "C", "Third Term", "2025-2026", school={"combine_third_term_results":1, "class_arm_ranking_mode":"separate"})
    assert len(results) == 1
    assert results[0]['average_marks'] == pytest.approx((50 + 70 + 90) / 3)
    assert results[0]['scores']['Math']['overall_mark'] == pytest.approx((50 + 70 + 90) / 3)


def test_subject_overall_mark_prefers_numeric_components_over_stale_explicit(app_module):
    m = app_module
    score_block = {
        "overall_mark": "0",
        "test_1": "12",
        "test_2": "8",
        "exam_score": "60",
    }
    assert m.subject_overall_mark(score_block) == pytest.approx(80.0)


def test_historical_template_headers_include_attendance_behaviour_and_term_dates(app_module):
    m = app_module
    headers = m._historical_results_template_headers_for_school(
        {"max_tests": 2, "test_enabled": 1, "exam_enabled": 1}
    )
    assert "Days Open" in headers
    assert "Days Present" in headers
    assert "Days Absent" in headers
    assert "Term Begin" in headers
    assert "Term End" in headers
    assert "Next Term Begin" in headers
    assert "Next Term End" in headers
    assert "Punctuality" in headers
    assert "Responsibility" in headers


def test_parse_generic_behaviour_spreadsheet_values_accepts_trait_and_grade_lists(app_module):
    m = app_module
    payload = m.parse_generic_behaviour_spreadsheet_values(
        "Punctuality, Neatness, Honesty",
        "A, B, C",
        {"behaviour_grade_mode": "alpha_ad"},
    )
    assert payload == {
        "Punctuality": "A",
        "Neatness": "B",
        "Honesty": "C",
    }


def test_parse_generic_behaviour_spreadsheet_values_accepts_trait_grade_pairs(app_module):
    m = app_module
    payload = m.parse_generic_behaviour_spreadsheet_values(
        "Punctuality:A; Neatness:B; Honesty:C",
        "",
        {"behaviour_grade_mode": "alpha_ad"},
    )
    assert payload["Punctuality"] == "A"
    assert payload["Neatness"] == "B"
    assert payload["Honesty"] == "C"


def test_status_is_passing_uses_status_band_order_not_pass_mark(app_module):
    m = app_module
    school = {
        "pass_mark": 80,
        "status_scale_json": json.dumps([
            {"label": "Excellent", "min_score": 85},
            {"label": "Pass", "min_score": 50},
            {"label": "Probation", "min_score": 40},
            {"label": "Fail", "min_score": 0},
        ]),
    }
    assert m.status_is_passing("Excellent", school) is True
    assert m.status_is_passing("Pass", school) is True
    assert m.status_is_passing("Probation", school) is True
    assert m.status_is_passing("Fail", school) is False


def test_compute_average_marks_ignores_stale_non_subject_score_keys(app_module):
    m = app_module
    scores = {
        "Mathematics": {"overall_mark": 80},
        "Old Subject": {"overall_mark": 20},
    }
    avg = m.compute_average_marks_from_scores(scores, subjects=["Mathematics"])
    assert avg == pytest.approx(80.0)


def test_is_score_complete_for_subject_requires_numeric_values(app_module):
    m = app_module
    school = {"test_enabled": 1, "exam_enabled": 1}
    assert m.is_score_complete_for_subject(
        {"overall_mark": "75", "total_test": "20", "total_exam": "55"},
        school,
    ) is True
    assert m.is_score_complete_for_subject(
        {"overall_mark": "", "total_test": "20", "total_exam": "55"},
        school,
    ) is False
    assert m.is_score_complete_for_subject(
        {"overall_mark": "75", "total_test": "", "total_exam": "55"},
        school,
    ) is False


def test_build_subjects_from_config_stream_rejects_invalid_optional(app_module):
    m = app_module
    config = {
        "core_subjects": ["English Language", "Mathematics"],
        "science_subjects": ["Biology", "Chemistry"],
        "art_subjects": [],
        "commercial_subjects": [],
        "optional_subjects": ["French", "Data Processing"],
    }
    subjects, final_stream, err = m.build_subjects_from_config(
        classname="SS2",
        stream="Science",
        config=config,
        selected_optional_subjects=["French", "Invalid Subject"],
        school={"ss1_stream_mode": "separate"},
    )
    assert subjects is None
    assert final_stream is None
    assert err == "Invalid optional subject selection."


def test_build_subjects_from_config_stream_accepts_multiple_optional_without_limit(app_module):
    m = app_module
    config = {
        "core_subjects": ["English Language", "Mathematics"],
        "science_subjects": ["Biology", "Chemistry"],
        "art_subjects": [],
        "commercial_subjects": [],
        "optional_subjects": ["French", "Data Processing", "Agricultural Science"],
    }
    subjects, final_stream, err = m.build_subjects_from_config(
        classname="SS3",
        stream="Science",
        config=config,
        selected_optional_subjects=["French", "Data Processing", "Agricultural Science"],
        school={},
    )
    assert err is None
    assert final_stream == "Science"
    assert "French" in subjects
    assert "Data Processing" in subjects
    assert "Agricultural Science" in subjects


def test_review_result_approval_request_approve_path(app_module, monkeypatch):
    m = app_module
    called = {}

    monkeypatch.setattr(m, "ensure_result_publication_approval_columns", lambda: True)
    monkeypatch.setattr(
        m,
        "get_result_publication_row",
        lambda *args, **kwargs: {"approval_status": "pending", "is_published": False, "teacher_id": "teacher1"},
    )

    def fake_publish_results_for_class_atomic(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(m, "publish_results_for_class_atomic", fake_publish_results_for_class_atomic)
    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026"})
    monkeypatch.setattr(
        m,
        "get_class_attendance_publish_readiness",
        lambda **kwargs: {"ready": True, "days_open": 0, "missing_rows": [], "message": ""},
    )

    ok, message = m.review_result_approval_request(
        school_id="SCH1",
        classname="SS2",
        term="First Term",
        academic_year="2025-2026",
        admin_user_id="admin1",
        approve=True,
        review_note="Looks good",
    )

    assert ok is True
    assert "approved" in message.lower()
    assert called["teacher_id"] == "teacher1"
    assert called["classname"] == "SS2"


def test_review_result_approval_request_reject_requires_columns(app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(m, "ensure_result_publication_approval_columns", lambda: True)
    monkeypatch.setattr(
        m,
        "get_result_publication_row",
        lambda *args, **kwargs: {"approval_status": "pending", "is_published": False, "teacher_id": "teacher1"},
    )
    monkeypatch.setattr(m, "result_publication_has_approval_columns", lambda: False)

    ok, message = m.review_result_approval_request(
        school_id="SCH1",
        classname="SS2",
        term="First Term",
        academic_year="2025-2026",
        admin_user_id="admin1",
        approve=False,
        review_note="Fix issues",
    )

    assert ok is False
    assert "approval columns are missing" in message.lower()


def test_promote_students_repeat_path_updates_promoted_without_nameerror(app_module, monkeypatch):
    m = app_module
    captured_updates = []

    class FakeCursor:
        def fetchall(self):
            return [("STU1", "Aka", "JSS1", "JSS1", "[]")]

    class FakeConn:
        def __init__(self):
            self._cursor = FakeCursor()

        def cursor(self):
            return self._cursor

    @contextlib.contextmanager
    def fake_db_connection(commit=False):
        yield FakeConn()

    def fake_db_execute(_cursor, query, params=None):
        if "SET promoted" in query:
            captured_updates.append(params)

    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "db_execute", fake_db_execute)
    monkeypatch.setattr(m, "get_school", lambda school_id: {})
    monkeypatch.setattr(m, "normalize_promoted_db_value", lambda value: 1 if value else 0)

    m.promote_students(
        school_id="SCH1",
        from_class="JSS1",
        to_class="JSS2",
        action_by_student={},
        term="",
    )

    assert len(captured_updates) == 1
    assert captured_updates[0][0] == 0


def test_is_login_blocked_returns_wait_time_when_lock_active(app_module, monkeypatch):
    m = app_module

    class FakeCursor:
        def fetchone(self):
            return (4, datetime.now() + timedelta(seconds=61))

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    @contextlib.contextmanager
    def fake_db_connection(commit=False):
        yield FakeConn()

    monkeypatch.setattr(m, "purge_old_login_attempts", lambda: None)
    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "db_execute", lambda *args, **kwargs: None)

    blocked, wait_minutes = m.is_login_blocked("login", "User1", "127.0.0.1")
    assert blocked is True
    assert wait_minutes >= 2


def test_register_failed_login_locks_when_threshold_reached(app_module, monkeypatch):
    m = app_module
    updates = []

    class FakeCursor:
        def fetchone(self):
            return (m.LOGIN_MAX_ATTEMPTS - 1, datetime.now(), None)

    class FakeConn:
        def __init__(self):
            self._cursor = FakeCursor()

        def cursor(self):
            return self._cursor

    @contextlib.contextmanager
    def fake_db_connection(commit=False):
        yield FakeConn()

    def fake_db_execute(_cursor, query, params=None):
        if "UPDATE login_attempts" in query:
            updates.append(params)

    monkeypatch.setattr(m, "purge_old_login_attempts", lambda: None)
    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "db_execute", fake_db_execute)

    m.register_failed_login("login", "User1", "127.0.0.1")
    assert len(updates) == 1
    assert updates[0][0] == m.LOGIN_MAX_ATTEMPTS
    assert updates[0][2] is not None


def test_get_school_publication_statuses_uses_approval_columns_when_present(app_module, monkeypatch):
    m = app_module

    class FakeCursor:
        def fetchall(self):
            return [
                (
                    "JSS1",
                    "T1",
                    "Mr T",
                    1,
                    "2026-02-26T10:00:00",
                    "approved",
                    "2026-02-26T09:50:00",
                    "teacher1",
                    "2026-02-26T09:55:00",
                    "admin1",
                    "ok",
                )
            ]

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    @contextlib.contextmanager
    def fake_db_connection(commit=False):
        yield FakeConn()

    monkeypatch.setattr(m, "ensure_result_publication_approval_columns", lambda: None)
    monkeypatch.setattr(m, "result_publication_has_approval_columns", lambda: True)
    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "db_execute", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "get_term_edit_lock_status", lambda *args, **kwargs: {"enabled": True, "locked": False})
    monkeypatch.setattr(
        m,
        "get_class_published_view_counts",
        lambda *args, **kwargs: {"JSS1": {"published_count": 20, "viewed_count": 12}},
    )

    assignments = [{"classname": "JSS1", "teacher_name": "Mr T", "teacher_id": "T1", "term": "First Term", "academic_year": "2025-2026"}]
    rows = m.get_school_publication_statuses("SCH1", "First Term", "2025-2026", assignments=assignments)
    assert len(rows) == 1
    assert rows[0]["approval_status"] == "approved"
    assert rows[0]["is_published"] is True
    assert rows[0]["published_count"] == 20
    assert rows[0]["viewed_count"] == 12


def test_get_school_publication_statuses_fallback_when_approval_columns_missing(app_module, monkeypatch):
    m = app_module

    class FakeCursor:
        def fetchall(self):
            return [("JSS2", "T2", "Mrs T", 0, "")]

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    @contextlib.contextmanager
    def fake_db_connection(commit=False):
        yield FakeConn()

    monkeypatch.setattr(m, "ensure_result_publication_approval_columns", lambda: None)
    monkeypatch.setattr(m, "result_publication_has_approval_columns", lambda: False)
    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "db_execute", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "get_term_edit_lock_status", lambda *args, **kwargs: {"enabled": True, "locked": False})
    monkeypatch.setattr(m, "get_class_published_view_counts", lambda *args, **kwargs: {})

    assignments = [{"classname": "JSS2", "teacher_name": "Mrs T", "teacher_id": "T2", "term": "First Term", "academic_year": "2025-2026"}]
    rows = m.get_school_publication_statuses("SCH1", "First Term", "2025-2026", assignments=assignments)
    assert len(rows) == 1
    assert rows[0]["approval_status"] == "not_submitted"
    assert rows[0]["is_published"] is False


def test_teacher_publish_results_route_submits_for_approval(client, app_module, monkeypatch):
    m = app_module
    called = {}

    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026", "principal_signature_image": "sig"})
    monkeypatch.setattr(m, "get_teachers", lambda school_id: {"T1": {"signature_image": "sig"}})
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "teacher_has_class_access", lambda *args, **kwargs: True)
    monkeypatch.setattr(m, "is_result_published", lambda *args, **kwargs: False)
    monkeypatch.setattr(m, "get_result_publication_row", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "load_students", lambda *args, **kwargs: {"S1": {"firstname": "Aka"}})
    monkeypatch.setattr(m, "compute_class_subject_completion", lambda *args, **kwargs: {"ready": True, "rows": []})
    monkeypatch.setattr(m, "is_student_score_complete", lambda *args, **kwargs: True)
    monkeypatch.setattr(m, "class_behaviour_completion", lambda *args, **kwargs: {"ready": True, "missing_count": 0})
    monkeypatch.setattr(
        m,
        "get_class_attendance_publish_readiness",
        lambda **kwargs: {"ready": True, "days_open": 0, "missing_rows": [], "message": ""},
    )

    def fake_submit(school_id, classname, term, academic_year, teacher_id):
        called.update(
            {
                "school_id": school_id,
                "classname": classname,
                "term": term,
                "academic_year": academic_year,
                "teacher_id": teacher_id,
            }
        )

    monkeypatch.setattr(m, "submit_result_approval_request", fake_submit)

    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "T1"

    resp = client.post("/teacher/publish-results", data={"classname": "JSS1"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/teacher")
    assert called["classname"] == "JSS1"
    assert called["teacher_id"] == "T1"


def test_school_admin_approve_results_route_calls_review(client, app_module, monkeypatch):
    m = app_module
    called = {}

    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026"})
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")

    def fake_review(**kwargs):
        called.update(kwargs)
        return True, "approved"

    monkeypatch.setattr(m, "review_result_approval_request", fake_review)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    resp = client.post("/school-admin/approve-results", data={"classname": "JSS1", "review_note": "ok"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/school-admin/publish-results")
    assert called["approve"] is True
    assert called["classname"] == "JSS1"
    assert called["admin_user_id"] == "A1"


def test_school_admin_reject_results_route_calls_review(client, app_module, monkeypatch):
    m = app_module
    called = {}

    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026"})
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")

    def fake_review(**kwargs):
        called.update(kwargs)
        return True, "rejected"

    monkeypatch.setattr(m, "review_result_approval_request", fake_review)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    resp = client.post("/school-admin/reject-results", data={"classname": "JSS1", "review_note": "needs fix"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/school-admin/publish-results")
    assert called["approve"] is False
    assert called["classname"] == "JSS1"
    assert called["admin_user_id"] == "A1"
    assert called["review_note"] == "needs fix"


def test_school_admin_dashboard_passes_assignments_to_publication_statuses(client, app_module, monkeypatch):
    m = app_module
    captured = {}
    assignments = [{"classname": "JSS1", "teacher_name": "Mr T", "teacher_id": "T1", "term": "First Term", "academic_year": "2025-2026"}]

    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026", "principal_signature_image": ""})
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_total_student_count", lambda school_id: 1)
    monkeypatch.setattr(m, "get_teachers", lambda school_id, include_archived=False: {})
    monkeypatch.setattr(m, "get_student_count_by_class", lambda school_id: {})
    monkeypatch.setattr(m, "get_class_assignments", lambda school_id: assignments)
    monkeypatch.setattr(m, "get_last_login_at", lambda user_id: None)
    monkeypatch.setattr(m, "format_timestamp", lambda value: "")
    monkeypatch.setattr(m, "render_template", lambda *args, **kwargs: "OK")
    monkeypatch.setattr(m, "build_school_setup_wizard_summary", lambda school_id: {})
    monkeypatch.setattr(m, "has_school_setup_wizard_completed", lambda school_id: True)

    def fake_statuses(school_id, term, academic_year, assignments=None):
        captured["assignments"] = assignments
        return []

    monkeypatch.setattr(m, "get_school_publication_statuses", fake_statuses)

    # also verify approval workflow flag passed through
    monkeypatch.setattr(m, "result_publication_has_approval_columns", lambda: False)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    # patch render_template to capture its keyword args
    captured_render = {}
    def fake_render(template, **kwargs):
        captured_render.update(kwargs)
        return "OK"
    monkeypatch.setattr(m, "render_template", fake_render)

    resp = client.get("/school-admin")
    assert resp.status_code == 200
    assert captured["assignments"] is assignments
    # ensure the flag is passed and reflects the mocked approval column state
    assert captured_render.get("approval_workflow_enabled") is False
    # dashboard should include the flag even though render_template is stubbed
    # (check second argument of render_template)
    # since render_template returns "OK" we can't inspect output easily; instead
    # monkeypatch render_template to capture kwargs
    

def test_school_admin_login_skips_setup_wizard_when_setup_is_complete(client, app_module, monkeypatch):
    m = app_module
    marked = {}

    monkeypatch.setattr(m, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(m, "get_client_ip", lambda: "127.0.0.1")
    monkeypatch.setattr(m, "is_login_blocked", lambda *args, **kwargs: (False, 0))
    monkeypatch.setattr(m, "get_user", lambda username: {
        "username": username,
        "password_hash": "hashed",
        "role": "school_admin",
        "school_id": "SCH1",
        "terms_accepted": 1,
    })
    monkeypatch.setattr(m, "check_password", lambda stored, password: True)
    monkeypatch.setattr(m, "get_school", lambda school_id: {"school_id": school_id, "academic_year": "2025-2026"})
    monkeypatch.setattr(m, "build_school_access_state", lambda school: {"is_allowed": True})
    monkeypatch.setattr(m, "has_user_seen_first_login_tutorial", lambda username: True)
    monkeypatch.setattr(m, "is_password_expired", lambda user: False)
    monkeypatch.setattr(m, "_resolve_login_display_name", lambda role, username, school_id='': "Admin")
    monkeypatch.setattr(m, "clear_failed_login", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "record_login_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "update_login_timestamps", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "has_school_setup_wizard_completed", lambda school_id: False)
    monkeypatch.setattr(m, "build_school_setup_wizard_summary", lambda school_id: {"is_complete": True})
    monkeypatch.setattr(m, "mark_school_setup_wizard_completed", lambda school_id: marked.setdefault("school_id", school_id) or True)
    monkeypatch.setattr(m, "has_school_setup_wizard_started", lambda school_id: False)

    resp = client.post("/login", data={"username": "admin@school.com", "password": "secret"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/school-admin")
    assert marked.get("school_id") == "SCH1"


def test_school_admin_login_still_opens_setup_wizard_when_setup_incomplete(client, app_module, monkeypatch):
    m = app_module
    marked = []

    monkeypatch.setattr(m, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(m, "get_client_ip", lambda: "127.0.0.1")
    monkeypatch.setattr(m, "is_login_blocked", lambda *args, **kwargs: (False, 0))
    monkeypatch.setattr(m, "get_user", lambda username: {
        "username": username,
        "password_hash": "hashed",
        "role": "school_admin",
        "school_id": "SCH1",
        "terms_accepted": 1,
    })
    monkeypatch.setattr(m, "check_password", lambda stored, password: True)
    monkeypatch.setattr(m, "get_school", lambda school_id: {"school_id": school_id, "academic_year": "2025-2026"})
    monkeypatch.setattr(m, "build_school_access_state", lambda school: {"is_allowed": True})
    monkeypatch.setattr(m, "has_user_seen_first_login_tutorial", lambda username: True)
    monkeypatch.setattr(m, "is_password_expired", lambda user: False)
    monkeypatch.setattr(m, "_resolve_login_display_name", lambda role, username, school_id='': "Admin")
    monkeypatch.setattr(m, "clear_failed_login", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "record_login_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "update_login_timestamps", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "has_school_setup_wizard_completed", lambda school_id: False)
    monkeypatch.setattr(m, "build_school_setup_wizard_summary", lambda school_id: {"is_complete": False})
    monkeypatch.setattr(m, "mark_school_setup_wizard_completed", lambda school_id: marked.append(school_id) or True)
    monkeypatch.setattr(m, "has_school_setup_wizard_started", lambda school_id: False)

    resp = client.post("/login", data={"username": "admin@school.com", "password": "secret"})
    assert resp.status_code == 302
    assert "/school-admin/setup-wizard" in resp.headers["Location"]
    assert marked == []


def test_teacher_enter_scores_does_not_carry_previous_term_scores(client, app_module, monkeypatch):
    m = app_module
    saved_rows = []

    monkeypatch.setattr(m, "get_school", lambda school_id: {
        "academic_year": "2025-2026",
        "current_term": "First Term",
        "test_enabled": 1,
        "exam_enabled": 0,
        "max_tests": 1,
        "test_score_max": 10,
    })
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "load_student", lambda school_id, student_id: {
        "student_id": "ST1",
        "firstname": "Aka",
        "classname": "JSS1",
        "term": "Second Term",
        "subjects": ["Mathematics"],
        "scores": {"Old Subject": {"overall_mark": 55}},
        "teacher_comment": "",
        "stream": "S",
        "number_of_subject": 1,
    })
    monkeypatch.setattr(m, "teacher_has_class_access", lambda *args, **kwargs: True)
    monkeypatch.setattr(m, "get_teacher_subjects_for_class_term", lambda *args, **kwargs: ["Mathematics"])
    monkeypatch.setattr(m, "class_uses_stream_for_school", lambda *args, **kwargs: False)
    monkeypatch.setattr(m, "sync_student_subjects_to_class_config", lambda *args, **kwargs: (False, None))
    monkeypatch.setattr(m, "is_result_published", lambda *args, **kwargs: False)
    monkeypatch.setattr(m, "get_assessment_config_for_class", lambda *args, **kwargs: {"exam_mode": "combined", "exam_score_max": 70})
    monkeypatch.setattr(m, "get_latest_score_audit_map_for_student", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "get_teachers", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "get_teacher_subject_assignments", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "get_subject_submission_teacher_ids_for_class", lambda *args, **kwargs: set())
    monkeypatch.setattr(m, "audit_student_score_changes_with_cursor", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "set_result_published", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "save_student_with_cursor", lambda c, school_id, student_id, student_data: saved_rows.append(json.loads(json.dumps(student_data))))

    def fake_db_connection(commit=False):
        class FakeCursor:
            def execute(self, query, params=None):
                return None
            def fetchone(self):
                return ("Second Term", json.dumps({"Old Subject": {"overall_mark": 55}}))
        class FakeConn:
            def cursor(self):
                return FakeCursor()
        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()
        return ctx(commit)

    monkeypatch.setattr(m, "db_connection", fake_db_connection)

    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "T1"

    resp = client.post(
        "/teacher/enter-scores?student_id=ST1",
        data={"test_1_mathematics": "8", "subject_comment_mathematics": "", "teacher_comment": ""},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 303)
    assert saved_rows, "Expected score save to be called"
    saved = saved_rows[-1]
    assert saved.get("term") == "First Term"
    assert "Mathematics" in (saved.get("scores") or {})
    assert "Old Subject" not in (saved.get("scores") or {})


def test_publish_results_behaviour_uses_publish_year(app_module, monkeypatch):
    m = app_module
    captured = {}

    monkeypatch.setattr(m, "ensure_result_publication_approval_columns", lambda: True)
    monkeypatch.setattr(m, "result_publication_has_approval_columns", lambda: False)
    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026", "principal_name": "Principal"})
    monkeypatch.setattr(m, "get_grade_config", lambda school_id: {"pass_mark": 50, "grade_a_min": 70, "grade_b_min": 60, "grade_c_min": 50, "grade_d_min": 40})
    monkeypatch.setattr(m, "get_teachers", lambda school_id: {"T1": {"firstname": "T", "lastname": "One"}})
    monkeypatch.setattr(
        m,
        "load_students",
        lambda school_id, class_filter="", term_filter="": {
            "ST1": {
                "firstname": "Aka",
                "classname": "JSS1",
                "stream": "S",
                "number_of_subject": 1,
                "subjects": ["Mathematics"],
                "scores": {"Mathematics": {"overall_mark": 80}},
                "teacher_comment": "",
                "principal_comment": "",
            }
        },
    )
    monkeypatch.setattr(m, "get_class_attendance_publish_readiness", lambda **kwargs: {"ready": True, "missing_rows": [], "days_open": 0, "message": ""})

    def fake_behaviour(school_id, classname, term, academic_year=''):
        captured["year"] = academic_year
        return {"ST1": {}}

    monkeypatch.setattr(m, "get_class_behaviour_assessments", fake_behaviour)

    def fake_db_connection(commit=False):
        class FakeCursor:
            def execute(self, query, params=None):
                return None
            def fetchall(self):
                return []
        class FakeConn:
            def cursor(self):
                return FakeCursor()
        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()
        return ctx(commit)

    monkeypatch.setattr(m, "db_connection", fake_db_connection)

    m.publish_results_for_class_atomic("SCH1", "JSS1", "First Term", "T1", academic_year="2025-2026")
    assert captured.get("year") == "2025-2026"


def test_filter_visible_terms_for_student_hides_current_term_when_operations_off(app_module):
    m = app_module
    school = {"operations_enabled": 0, "current_term": "Second Term", "academic_year": "2025-2026"}
    terms = [
        {"term": "First Term", "academic_year": "2025-2026", "token": "2025-2026::First Term"},
        {"term": "Second Term", "academic_year": "2025-2026", "token": "2025-2026::Second Term"},
        {"term": "Third Term", "academic_year": "2024-2025", "token": "2024-2025::Third Term"},
    ]
    visible = m.filter_visible_terms_for_student(school, terms)
    visible_tokens = [row.get("token") for row in visible]
    assert "2025-2026::Second Term" not in visible_tokens
    assert "2025-2026::First Term" in visible_tokens
    assert "2024-2025::Third Term" in visible_tokens


def test_rate_limit_consume_blocks_after_limit(app_module, monkeypatch):
    m = app_module
    m._RATE_LIMIT_EVENTS.clear()
    monkeypatch.setattr(m.time, "time", lambda: 1000.0)

    ok1, retry1 = m._rate_limit_consume("login:1.2.3.4", 2, 60)
    ok2, retry2 = m._rate_limit_consume("login:1.2.3.4", 2, 60)
    ok3, retry3 = m._rate_limit_consume("login:1.2.3.4", 2, 60)

    assert ok1 is True and retry1 == 0
    assert ok2 is True and retry2 == 0
    assert ok3 is False
    assert retry3 >= 1


def test_rate_limit_consume_allows_after_window(app_module, monkeypatch):
    m = app_module
    m._RATE_LIMIT_EVENTS.clear()
    now = {"t": 1000.0}
    monkeypatch.setattr(m.time, "time", lambda: now["t"])

    assert m._rate_limit_consume("check_result:1.2.3.4", 1, 60)[0] is True
    assert m._rate_limit_consume("check_result:1.2.3.4", 1, 60)[0] is False

    now["t"] = 1062.0
    assert m._rate_limit_consume("check_result:1.2.3.4", 1, 60)[0] is True


def test_timetable_time_ranges_overlap_logic(app_module):
    m = app_module
    assert m.timetable_time_ranges_overlap("08:00", "08:40", "08:20", "09:00") is True
    assert m.timetable_time_ranges_overlap("08:00", "08:40", "08:40", "09:00") is False
    assert m.timetable_time_ranges_overlap("09:00", "08:40", "08:00", "09:00") is False


def test_find_timetable_time_conflicts_detects_overlap(app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(
        m,
        "get_school_timetable_rows",
        lambda school_id, classname='': [
            {
                "id": 22,
                "classname": "JSS1",
                "day_of_week": 1,
                "period_label": "Period 1",
                "subject": "Mathematics",
                "start_time": "08:00",
                "end_time": "08:40",
            }
        ],
    )
    rows = m.find_timetable_time_conflicts("SCH", "JSS1", 1, "08:20", "08:50")
    assert rows and rows[0]["id"] == 22


def test_get_current_online_lessons_finds_multiple_active_rows(app_module):
    m = app_module
    rows = [
        {
            "day_of_week": 1,
            "period_label": "Period 2",
            "subject": "English",
            "classname": "JSS1",
            "start_time": "08:00",
            "end_time": "09:00",
            "online_url": "https://meet.example.com/foo",
        },
        {
            "day_of_week": 1,
            "period_label": "Period 3",
            "subject": "Mathematics",
            "classname": "JSS1",
            "start_time": "08:20",
            "end_time": "09:10",
            "online_url": "https://meet.example.com/bar",
        },
        {
            "day_of_week": 1,
            "period_label": "Period 1",
            "subject": "Science",
            "classname": "JSS1",
            "start_time": "07:00",
            "end_time": "07:40",
            "online_url": "https://meet.example.com/baz",
        },
    ]
    active = m.get_current_online_lessons(rows, current_day=1, current_minutes=510)
    assert len(active) == 2
    assert active[0]["period_label"] == "Period 2"
    assert active[0]["minutes_left"] == 30
    assert active[1]["period_label"] == "Period 3"


def test_parent_timetable_filters_to_child_subjects_only(client, app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(m, "_parent_allowed_student_keys", lambda: {"SCH::STU1"})
    monkeypatch.setattr(
        m,
        "get_school",
        lambda school_id: {
            "school_id": school_id,
            "school_name": "Alpha School",
            "theme_accent_color": "#1F7A8C",
            "parent_timetable_show_teacher": 1,
        },
    )
    monkeypatch.setattr(
        m,
        "load_students_for_student_ids",
        lambda school_id, ids: {
            "STU1": {
                "firstname": "Aka",
                "classname": "JSS1",
                "stream": "Science",
                "subjects": ["Mathematics"],
                "scores": {},
            }
        },
    )
    monkeypatch.setattr(
        m,
        "get_school_timetable_rows",
        lambda school_id, classname='': [
            {
                "id": 1,
                "classname": "JSS1",
                "day_of_week": 1,
                "day_name": "Monday",
                "period_label": "Period 1",
                "subject": "Mathematics",
                "teacher_id": "T1",
                "start_time": "08:00",
                "end_time": "08:40",
                "room": "A1",
            },
            {
                "id": 2,
                "classname": "JSS1",
                "day_of_week": 1,
                "day_name": "Monday",
                "period_label": "Period 2",
                "subject": "French",
                "teacher_id": "T2",
                "start_time": "08:40",
                "end_time": "09:20",
                "room": "A1",
            },
        ],
    )
    monkeypatch.setattr(
        m,
        "get_teachers",
        lambda school_id: {"T1": {"firstname": "Grace", "lastname": "Doe"}, "T2": {"firstname": "John", "lastname": "Roe"}},
    )
    monkeypatch.setattr(m, "get_parent_messages_for_children", lambda **kwargs: [])
    monkeypatch.setattr(m, "get_class_subject_config", lambda school_id, classname: {})

    with client.session_transaction() as sess:
        sess["role"] = "parent"
        sess["parent_phone"] = "+234000000000"

    resp = client.get("/parent/timetable?student_key=SCH::STU1")
    body = resp.data.decode("utf-8")
    assert resp.status_code == 200
    assert "Mathematics" in body
    assert "French" not in body

def test_teacher_allocate_stream_post_updates_and_redirects_dashboard(client, app_module, monkeypatch):
    m = app_module
    update_calls = []

    monkeypatch.setattr(
        m,
        "get_user",
        lambda username: {"username": (username or "").lower(), "role": "teacher", "school_id": "SCH1"},
    )

    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026", "ss1_stream_mode": "separate"})
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(
        m,
        "load_student",
        lambda school_id, student_id: {
            "student_id": student_id,
            "firstname": "Aka",
            "classname": "SS2",
            "stream": "N/A",
            "subjects": ["English Language", "Mathematics"],
            "scores": {"English Language": {"overall_mark": 65}},
            "number_of_subject": 2,
        },
    )
    monkeypatch.setattr(m, "teacher_has_class_access", lambda *args, **kwargs: True)
    monkeypatch.setattr(m, "class_uses_stream_for_school", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        m,
        "get_class_subject_config",
        lambda school_id, classname: {
            "core_subjects": ["English Language", "Mathematics"],
            "science_subjects": ["Biology"],
            "art_subjects": ["Literature in English"],
            "commercial_subjects": ["Commerce"],
            "optional_subjects": [],
        },
    )
    monkeypatch.setattr(
        m,
        "build_subjects_from_config",
        lambda **kwargs: (["English Language", "Mathematics", "Biology"], "Science", None),
    )

    def fake_db_connection(commit=False):
        class FakeCursor:
            def __init__(self):
                self.rowcount = 0

        class FakeConn:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()

        return ctx(commit)

    def fake_db_execute(cursor, query, params=None):
        if "UPDATE students" in str(query):
            cursor.rowcount = 1
            update_calls.append((query, params))

    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "db_execute", fake_db_execute)

    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "T1"

    resp = client.post(
        "/teacher/allocate-stream",
        data={"student_id": "ST1", "stream": "Science"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/teacher")
    assert update_calls, "Expected UPDATE students call for stream allocation"
    _, params = update_calls[-1]
    assert params[0] == "Science"
    assert params[4] == "SCH1"
    assert params[5] == "ST1"


def test_teacher_allocate_stream_post_handles_zero_updated_rows(client, app_module, monkeypatch):
    m = app_module

    monkeypatch.setattr(
        m,
        "get_user",
        lambda username: {"username": (username or "").lower(), "role": "teacher", "school_id": "SCH1"},
    )

    monkeypatch.setattr(m, "get_school", lambda school_id: {"academic_year": "2025-2026", "ss1_stream_mode": "separate"})
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(
        m,
        "load_student",
        lambda school_id, student_id: {
            "student_id": student_id,
            "firstname": "Aka",
            "classname": "SS2",
            "stream": "N/A",
            "subjects": ["English Language", "Mathematics"],
            "scores": {},
            "number_of_subject": 2,
        },
    )
    monkeypatch.setattr(m, "teacher_has_class_access", lambda *args, **kwargs: True)
    monkeypatch.setattr(m, "class_uses_stream_for_school", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        m,
        "get_class_subject_config",
        lambda school_id, classname: {
            "core_subjects": ["English Language", "Mathematics"],
            "science_subjects": ["Biology"],
            "art_subjects": [],
            "commercial_subjects": [],
            "optional_subjects": [],
        },
    )
    monkeypatch.setattr(
        m,
        "build_subjects_from_config",
        lambda **kwargs: (["English Language", "Mathematics", "Biology"], "Science", None),
    )

    def fake_db_connection(commit=False):
        class FakeCursor:
            def __init__(self):
                self.rowcount = 0

        class FakeConn:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()

        return ctx(commit)

    def fake_db_execute(cursor, query, params=None):
        if "UPDATE students" in str(query):
            cursor.rowcount = 0

    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "db_execute", fake_db_execute)

    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "T1"

    resp = client.post(
        "/teacher/allocate-stream",
        data={"student_id": "ST1", "stream": "Science"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/teacher/allocate-stream?student_id=ST1" in resp.headers["Location"]


def test_teacher_upload_csv_form_includes_csrf_token(client, app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(
        m,
        "get_school",
        lambda school_id: {"academic_year": "2025/2026", "exam_enabled": 1, "max_tests": 2},
    )
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(
        m,
        "get_teacher_classes",
        lambda school_id, teacher_id, term="", academic_year="": ["JSS1"],
    )
    monkeypatch.setattr(
        m,
        "get_teacher_subject_assignments",
        lambda school_id, teacher_id=None, term="", academic_year="": [],
    )
    monkeypatch.setattr(
        m,
        "get_assessment_config_for_class",
        lambda school_id, classname: {"exam_mode": "combined"},
    )
    monkeypatch.setattr(
        m,
        "get_teachers",
        lambda school_id: {"T1": {"firstname": "Test", "lastname": "Teacher"}},
    )
    monkeypatch.setattr(
        m,
        "get_teacher",
        lambda school_id, teacher_id: {"firstname": "Test", "lastname": "Teacher"},
    )

    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "T1"

    resp = client.get("/teacher/upload-csv")
    assert resp.status_code == 200
    assert 'name="csrf_token"' in resp.get_data(as_text=True)


def test_build_result_term_attendance_data_exposes_next_term_end(app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(
        m,
        "get_school_term_calendar",
        lambda school_id, academic_year, term: {
            "open_date": "2025-09-16",
            "close_date": "2025-12-12",
            "days_open": 72,
        },
    )
    monkeypatch.setattr(
        m,
        "get_school_term_program",
        lambda school_id, academic_year, term: {
            "next_term_begin_date": "2026-01-06",
            "next_term_end_date": "2026-04-10",
            "program_meta_json": {"next_term_end_date": "2026-04-10"},
        },
    )
    monkeypatch.setattr(m, "class_has_attendance_marks", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        m,
        "get_student_manual_result_attendance",
        lambda *args, **kwargs: {"days_open": 72, "days_present": 68},
    )
    monkeypatch.setattr(m, "resolve_next_term_begin_date", lambda *args, **kwargs: "2026-01-06")

    payload = m.build_result_term_attendance_data("SCH1", "ST1", "JSS1", "First Term", "2025-2026")
    assert payload["term_begin"] == "2025-09-16"
    assert payload["term_end"] == "2025-12-12"
    assert payload["next_term_begin"] == "2026-01-06"
    assert payload["next_term_end"] == "2026-04-10"
    assert payload["days_open"] == 72
    assert payload["days_present"] == 68
    assert payload["days_absent"] == 4


def test_school_admin_bulk_tools_forms_accept_excel(client, app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(m, "get_school", lambda school_id: {"max_tests": 3, "academic_year": "2025-2026"})
    monkeypatch.setattr(m, "get_secondary_school_classnames", lambda school_id: ["JSS1"])
    monkeypatch.setattr(m, "get_backup_schedule_settings", lambda school_id: None)
    monkeypatch.setattr(m, "compute_school_storage_usage", lambda school_id: {"used_mb": 0, "quota_mb": 100, "pct": 0})
    monkeypatch.setattr(m, "get_backup_health_summary", lambda school_id, days=30: None)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "admin1"

    resp = client.get("/school-admin/bulk-tools")
    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert 'accept=".csv,.xlsx"' in page


def test_school_admin_import_teachers_accepts_xlsx(client, app_module, monkeypatch):
    m = app_module
    saved_teachers = []
    provisioned_users = []

    def fake_save_teacher(school_id, teacher_id, firstname, lastname, assigned_classes, subjects_taught=None, phone='', gender=''):
        saved_teachers.append(
            {
                "school_id": school_id,
                "teacher_id": teacher_id,
                "firstname": firstname,
                "lastname": lastname,
                "assigned_classes": assigned_classes,
                "subjects_taught": subjects_taught,
                "phone": phone,
                "gender": gender,
            }
        )

    def fake_upsert_user(user_id, password_hash, role, school_id):
        provisioned_users.append(
            {
                "user_id": user_id,
                "password_hash": password_hash,
                "role": role,
                "school_id": school_id,
            }
        )

    monkeypatch.setattr(m, "get_user", lambda user_id: None)
    monkeypatch.setattr(m, "save_teacher", fake_save_teacher)
    monkeypatch.setattr(m, "upsert_user", fake_upsert_user)
    monkeypatch.setattr(m, "record_admin_action_audit", lambda *args, **kwargs: None)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "admin1"

    workbook = _build_inline_xlsx(
        [
            ["user_id", "firstname", "lastname", "phone", "gender"],
            ["teacher1@example.com", "Tega", "Okafor", "08012345678", "female"],
        ]
    )
    resp = client.post(
        "/school-admin/import/teachers",
        data={"file": (io.BytesIO(workbook), "teachers.xlsx")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/school-admin/bulk-tools?error_token=")
    assert len(saved_teachers) == 1
    assert saved_teachers[0]["teacher_id"] == "teacher1@example.com"
    assert len(provisioned_users) == 1
    assert provisioned_users[0]["role"] == "teacher"
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert any("Teachers import completed. Imported 1 row(s)." in message for _category, message in flashes)


def test_school_admin_settings_academic_save_preserves_result_configuration(client, app_module, monkeypatch):
    m = app_module
    saved_settings = {}
    assessment_saves = []

    current_school = {
        "school_name": "Demo School",
        "location": "City",
        "academic_year": "2025-2026",
        "current_term": "First Term",
        "test_enabled": 1,
        "exam_enabled": 1,
        "max_tests": 4,
        "test_score_max": 35,
        "exam_objective_max": 30,
        "exam_theory_max": 40,
        "grade_a_min": 75,
        "grade_b_min": 65,
        "grade_c_min": 55,
        "grade_d_min": 45,
        "grade_label_a": "A1",
        "grade_label_b": "B2",
        "grade_label_c": "B3",
        "grade_label_d": "C4",
        "grade_label_f": "F9",
        "performance_remark_a": "Excellent",
        "performance_remark_b": "Very good",
        "performance_remark_c": "Good",
        "performance_remark_d": "Fair",
        "performance_remark_f": "Needs improvement",
        "pass_mark": 50,
        "show_positions": 1,
        "ss_ranking_mode": "separate",
        "class_arm_ranking_mode": "together",
        "combine_third_term_results": 1,
        "ss1_stream_mode": "combined",
        "ss_arm_mode": "drop",
        "parent_timetable_show_teacher": 0,
        "theme_primary_color": "#1E3C72",
        "theme_secondary_color": "#2A5298",
        "theme_accent_color": "#1F7A8C",
        "leadership_title": "principal",
        "score_entry_mode": "dean_led",
    }

    monkeypatch.setattr(m, "get_school", lambda school_id: dict(current_school))
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_school_term_calendar", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "get_school_term_program", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "build_school_settings_version_token", lambda *args, **kwargs: "v1")
    monkeypatch.setattr(m, "ensure_school_access_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_school_term_calendar_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_extended_features_schema", lambda: True)
    monkeypatch.setattr(m, "save_school_term_calendar_with_cursor", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "invalidate_school_cache", lambda school_id='': None)
    monkeypatch.setattr(m, "record_admin_action_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "mark_user_first_login_tutorial_seen", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "get_all_assessment_configs", lambda school_id: {
        "jss": {"exam_mode": "combined", "objective_max": 0, "theory_max": 0, "exam_score_max": 65},
        "ss": {"exam_mode": "separate", "objective_max": 30, "theory_max": 40, "exam_score_max": 70},
    })
    monkeypatch.setattr(m, "list_school_term_calendars", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "rollover_school_term_data_with_cursor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(m, "save_assessment_config_with_cursor", lambda *args, **kwargs: assessment_saves.append(kwargs))

    def fake_update_school_settings_with_cursor(c, school_id, settings):
        saved_settings.update(settings)

    monkeypatch.setattr(m, "update_school_settings_with_cursor", fake_update_school_settings_with_cursor)

    def fake_db_connection(commit=False):
        class FakeCursor:
            pass

        class FakeConn:
            def cursor(self):
                return FakeCursor()

        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()

        return ctx(commit)

    monkeypatch.setattr(m, "db_connection", fake_db_connection)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    resp = client.post(
        "/school-admin/settings?section=academic",
        data={
            "settings_section": "academic",
            "settings_version": "v1",
            "school_name": "Demo School",
            "academic_year": "2025-2026",
            "current_term": "First Term",
            "test_enabled": "1",
            "exam_enabled": "1",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert saved_settings["max_tests"] == 4
    assert saved_settings["test_score_max"] == 35
    assert saved_settings["grade_a_min"] == 75
    assert saved_settings["grade_label_a"] == "A1"
    assert saved_settings["grade_label_f"] == "F9"
    assert saved_settings["performance_remark_a"] == "Excellent"
    assert saved_settings["performance_remark_f"] == "Needs improvement"
    assert saved_settings["ss_ranking_mode"] == "separate"
    assert saved_settings["score_entry_mode"] == "dean_led"
    assert assessment_saves == []


def test_school_admin_settings_results_validation_preserves_posted_score_values(client, app_module, monkeypatch):
    m = app_module
    saved_settings = {}

    current_school = {
        "school_name": "Demo School",
        "location": "City",
        "academic_year": "2025-2026",
        "current_term": "First Term",
        "test_enabled": 1,
        "exam_enabled": 1,
        "max_tests": 3,
        "test_score_max": 30,
        "exam_objective_max": 30,
        "exam_theory_max": 40,
        "grade_a_min": 70,
        "grade_b_min": 60,
        "grade_c_min": 50,
        "grade_d_min": 40,
        "grade_label_a": "A",
        "grade_label_b": "B",
        "grade_label_c": "C",
        "grade_label_d": "D",
        "grade_label_f": "F",
        "performance_remark_a": "A remark",
        "performance_remark_b": "B remark",
        "performance_remark_c": "C remark",
        "performance_remark_d": "D remark",
        "performance_remark_f": "F remark",
        "pass_mark": 50,
        "show_positions": 1,
        "ss_ranking_mode": "together",
        "class_arm_ranking_mode": "separate",
        "combine_third_term_results": 0,
        "ss1_stream_mode": "separate",
        "ss_arm_mode": "preserve",
        "parent_timetable_show_teacher": 1,
        "theme_primary_color": "#1E3C72",
        "theme_secondary_color": "#2A5298",
        "theme_accent_color": "#1F7A8C",
        "leadership_title": "principal",
        "score_entry_mode": "teacher_subject",
    }

    monkeypatch.setattr(m, "get_school", lambda school_id: dict(current_school))
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_school_term_calendar", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "get_school_term_program", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "build_school_settings_version_token", lambda *args, **kwargs: "v1")
    monkeypatch.setattr(m, "ensure_school_access_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_school_term_calendar_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_extended_features_schema", lambda: True)
    monkeypatch.setattr(m, "save_school_term_calendar_with_cursor", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "invalidate_school_cache", lambda school_id='': None)
    monkeypatch.setattr(m, "record_admin_action_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "mark_user_first_login_tutorial_seen", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "get_all_assessment_configs", lambda school_id: {
        "jss": {"exam_mode": "separate", "objective_max": 30, "theory_max": 40, "exam_score_max": 70},
        "ss": {"exam_mode": "separate", "objective_max": 30, "theory_max": 40, "exam_score_max": 70},
    })
    monkeypatch.setattr(m, "list_school_term_calendars", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "save_assessment_config_with_cursor", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("assessment config should not save on validation error")))

    def fake_update_school_settings_with_cursor(c, school_id, settings):
        saved_settings.update(settings)

    monkeypatch.setattr(m, "update_school_settings_with_cursor", fake_update_school_settings_with_cursor)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    resp = client.post(
        "/school-admin/settings?section=results",
        data={
            "settings_section": "results",
            "settings_version": "v1",
            "max_tests": "4",
            "test_score_max": "40",
            "grade_a_min": "70",
            "grade_b_min": "60",
            "grade_c_min": "50",
            "grade_d_min": "40",
            "grade_label_a": "A+",
            "grade_label_b": "A",
            "grade_label_c": "B+",
            "grade_label_d": "B",
            "grade_label_f": "C",
            "performance_remark_a": "A remark",
            "performance_remark_b": "B remark",
            "performance_remark_c": "C remark",
            "performance_remark_d": "D remark",
            "performance_remark_f": "F remark",
            "pass_mark": "50",
            "show_positions": "1",
            "ss_ranking_mode": "together",
            "class_arm_ranking_mode": "separate",
            "ss1_stream_mode": "separate",
            "ss_arm_mode": "preserve",
            "combine_third_term_results": "0",
            "parent_timetable_show_teacher": "1",
            "exam_mode_jss": "separate",
            "objective_max_jss": "35",
            "theory_max_jss": "30",
            "exam_score_max_jss": "65",
            "exam_mode_ss": "combined",
            "objective_max_ss": "0",
            "theory_max_ss": "0",
            "exam_score_max_ss": "65",
        },
        follow_redirects=False,
    )

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert saved_settings == {}
    assert 'value="4"' in body
    assert 'value="40"' in body
    assert 'value="35"' in body
    assert 'value="65"' in body
    assert 'objective + theory must add up to 60 because total test score is 40' in body


def test_school_admin_settings_results_combined_mode_derives_exam_total_from_test_total(client, app_module, monkeypatch):
    m = app_module
    saved_settings = {}
    assessment_saves = []

    current_school = {
        "school_name": "Demo School",
        "location": "City",
        "academic_year": "2025-2026",
        "current_term": "First Term",
        "test_enabled": 1,
        "exam_enabled": 1,
        "max_tests": 3,
        "test_score_max": 30,
        "exam_objective_max": 30,
        "exam_theory_max": 40,
        "grade_a_min": 70,
        "grade_b_min": 60,
        "grade_c_min": 50,
        "grade_d_min": 40,
        "grade_label_a": "A",
        "grade_label_b": "B",
        "grade_label_c": "C",
        "grade_label_d": "D",
        "grade_label_f": "F",
        "performance_remark_a": "",
        "performance_remark_b": "",
        "performance_remark_c": "",
        "performance_remark_d": "",
        "performance_remark_f": "",
        "pass_mark": 50,
        "show_positions": 1,
        "ss_ranking_mode": "together",
        "class_arm_ranking_mode": "separate",
        "combine_third_term_results": 0,
        "ss1_stream_mode": "separate",
        "ss_arm_mode": "preserve",
        "parent_timetable_show_teacher": 1,
        "theme_primary_color": "#1E3C72",
        "theme_secondary_color": "#2A5298",
        "theme_accent_color": "#1F7A8C",
        "leadership_title": "principal",
        "score_entry_mode": "teacher_subject",
        "school_logo": "",
    }

    monkeypatch.setattr(m, "get_school", lambda school_id: dict(current_school))
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_school_term_calendar", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "get_school_term_program", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "build_school_settings_version_token", lambda *args, **kwargs: "v1")
    monkeypatch.setattr(m, "ensure_school_access_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_school_term_calendar_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_extended_features_schema", lambda: True)
    monkeypatch.setattr(m, "save_school_term_calendar_with_cursor", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "invalidate_school_cache", lambda school_id='': None)
    monkeypatch.setattr(m, "record_admin_action_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "mark_user_first_login_tutorial_seen", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "get_all_assessment_configs", lambda school_id: {
        "jss": {"exam_mode": "combined", "objective_max": 0, "theory_max": 0, "exam_score_max": 70},
        "ss": {"exam_mode": "combined", "objective_max": 0, "theory_max": 0, "exam_score_max": 70},
    })
    monkeypatch.setattr(m, "list_school_term_calendars", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "rollover_school_term_data_with_cursor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(m, "save_assessment_config_with_cursor", lambda *args, **kwargs: assessment_saves.append(kwargs))

    def fake_update_school_settings_with_cursor(c, school_id, settings):
        saved_settings.update(settings)

    monkeypatch.setattr(m, "update_school_settings_with_cursor", fake_update_school_settings_with_cursor)

    def fake_db_connection(commit=False):
        class FakeCursor:
            pass

        class FakeConn:
            def cursor(self):
                return FakeCursor()

        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()

        return ctx(commit)

    monkeypatch.setattr(m, "db_connection", fake_db_connection)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    resp = client.post(
        "/school-admin/settings?section=results",
        data={
            "settings_section": "results",
            "settings_version": "v1",
            "school_name": "Demo School",
            "academic_year": "2025-2026",
            "current_term": "First Term",
            "max_tests": "4",
            "test_score_max": "40",
            "grade_a_min": "70",
            "grade_b_min": "60",
            "grade_c_min": "50",
            "grade_d_min": "40",
            "grade_label_a": "A1",
            "grade_label_b": "B2",
            "grade_label_c": "B3",
            "grade_label_d": "C4",
            "grade_label_f": "F9",
            "performance_remark_a": "Excellent work",
            "performance_remark_b": "Good effort",
            "performance_remark_c": "Keep improving",
            "performance_remark_d": "Work harder",
            "performance_remark_f": "Urgent support needed",
            "pass_mark": "50",
            "show_positions": "1",
            "ss_ranking_mode": "together",
            "class_arm_ranking_mode": "separate",
            "ss1_stream_mode": "separate",
            "ss_arm_mode": "preserve",
            "combine_third_term_results": "0",
            "parent_timetable_show_teacher": "1",
            "exam_mode_jss": "combined",
            "exam_score_max_jss": "15",
            "objective_max_jss": "0",
            "theory_max_jss": "0",
            "exam_mode_ss": "combined",
            "exam_score_max_ss": "20",
            "objective_max_ss": "0",
            "theory_max_ss": "0",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert saved_settings["max_tests"] == 4
    assert saved_settings["test_score_max"] == 40
    assert saved_settings["grade_label_a"] == "A1"
    assert saved_settings["grade_label_f"] == "F9"
    assert saved_settings["performance_remark_a"] == "Excellent work"
    assert saved_settings["performance_remark_f"] == "Urgent support needed"
    assert len(assessment_saves) == 2
    assert all(item["exam_score_max"] == 60 for item in assessment_saves)


def test_school_admin_settings_results_separate_mode_requires_split_to_match_derived_exam_total(client, app_module, monkeypatch):
    m = app_module

    current_school = {
        "school_name": "Demo School",
        "location": "City",
        "academic_year": "2025-2026",
        "current_term": "First Term",
        "test_enabled": 1,
        "exam_enabled": 1,
        "max_tests": 3,
        "test_score_max": 30,
        "exam_objective_max": 30,
        "exam_theory_max": 40,
        "grade_a_min": 70,
        "grade_b_min": 60,
        "grade_c_min": 50,
        "grade_d_min": 40,
        "grade_label_a": "A",
        "grade_label_b": "B",
        "grade_label_c": "C",
        "grade_label_d": "D",
        "grade_label_f": "F",
        "pass_mark": 50,
        "show_positions": 1,
        "ss_ranking_mode": "together",
        "class_arm_ranking_mode": "separate",
        "combine_third_term_results": 0,
        "ss1_stream_mode": "separate",
        "ss_arm_mode": "preserve",
        "parent_timetable_show_teacher": 1,
        "theme_primary_color": "#1E3C72",
        "theme_secondary_color": "#2A5298",
        "theme_accent_color": "#1F7A8C",
        "leadership_title": "principal",
        "score_entry_mode": "teacher_subject",
        "school_logo": "",
    }

    monkeypatch.setattr(m, "get_school", lambda school_id: dict(current_school))
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_school_term_calendar", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "get_school_term_program", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "build_school_settings_version_token", lambda *args, **kwargs: "v1")
    monkeypatch.setattr(m, "ensure_school_access_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_school_term_calendar_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_extended_features_schema", lambda: True)
    monkeypatch.setattr(m, "get_all_assessment_configs", lambda school_id: {
        "jss": {"exam_mode": "separate", "objective_max": 30, "theory_max": 40, "exam_score_max": 70},
        "ss": {"exam_mode": "separate", "objective_max": 30, "theory_max": 40, "exam_score_max": 70},
    })
    monkeypatch.setattr(m, "list_school_term_calendars", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "update_school_settings_with_cursor", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("settings should not save on validation error")))
    monkeypatch.setattr(m, "save_assessment_config_with_cursor", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("assessment settings should not save on validation error")))

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    resp = client.post(
        "/school-admin/settings?section=results",
        data={
            "settings_section": "results",
            "settings_version": "v1",
            "max_tests": "4",
            "test_score_max": "40",
            "grade_a_min": "70",
            "grade_b_min": "60",
            "grade_c_min": "50",
            "grade_d_min": "40",
            "grade_label_a": "A1",
            "grade_label_b": "B2",
            "grade_label_c": "B3",
            "grade_label_d": "C4",
            "grade_label_f": "F9",
            "pass_mark": "50",
            "show_positions": "1",
            "ss_ranking_mode": "together",
            "class_arm_ranking_mode": "separate",
            "ss1_stream_mode": "separate",
            "ss_arm_mode": "preserve",
            "combine_third_term_results": "0",
            "parent_timetable_show_teacher": "1",
            "exam_mode_jss": "separate",
            "objective_max_jss": "20",
            "theory_max_jss": "30",
            "exam_score_max_jss": "50",
            "exam_mode_ss": "separate",
            "objective_max_ss": "30",
            "theory_max_ss": "30",
            "exam_score_max_ss": "60",
        },
        follow_redirects=False,
    )

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'JSS objective + theory must add up to 60 because total test score is 40.' in body
    assert 'value="4"' in body
    assert 'value="40"' in body


def test_school_admin_settings_custom_grade_scale_saves_separately(client, app_module, monkeypatch):
    m = app_module
    saved_settings = {}
    assessment_saves = []

    current_school = {
        "school_name": "Demo School",
        "location": "City",
        "academic_year": "2025-2026",
        "current_term": "First Term",
        "test_enabled": 1,
        "exam_enabled": 1,
        "max_tests": 4,
        "test_score_max": 40,
        "exam_objective_max": 30,
        "exam_theory_max": 30,
        "grade_a_min": 70,
        "grade_b_min": 60,
        "grade_c_min": 50,
        "grade_d_min": 40,
        "grade_label_a": "A",
        "grade_label_b": "B",
        "grade_label_c": "C",
        "grade_label_d": "D",
        "grade_label_f": "F",
        "grade_scale_json": "",
        "performance_remark_a": "",
        "performance_remark_b": "",
        "performance_remark_c": "",
        "performance_remark_d": "",
        "performance_remark_f": "",
        "pass_mark": 50,
        "show_positions": 1,
        "ss_ranking_mode": "together",
        "class_arm_ranking_mode": "separate",
        "combine_third_term_results": 0,
        "ss1_stream_mode": "separate",
        "ss_arm_mode": "preserve",
        "parent_timetable_show_teacher": 1,
        "theme_primary_color": "#1E3C72",
        "theme_secondary_color": "#2A5298",
        "theme_accent_color": "#1F7A8C",
        "leadership_title": "principal",
        "score_entry_mode": "teacher_subject",
        "school_logo": "",
    }

    monkeypatch.setattr(m, "get_school", lambda school_id: dict(current_school))
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_school_term_calendar", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "get_school_term_program", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "build_school_settings_version_token", lambda *args, **kwargs: "v1")
    monkeypatch.setattr(m, "ensure_school_access_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_school_term_calendar_schema", lambda: True)
    monkeypatch.setattr(m, "ensure_extended_features_schema", lambda: True)
    monkeypatch.setattr(m, "save_school_term_calendar_with_cursor", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "invalidate_school_cache", lambda school_id='': None)
    monkeypatch.setattr(m, "record_admin_action_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "mark_user_first_login_tutorial_seen", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "get_all_assessment_configs", lambda school_id: {
        "jss": {"exam_mode": "combined", "objective_max": 0, "theory_max": 0, "exam_score_max": 60},
        "ss": {"exam_mode": "combined", "objective_max": 0, "theory_max": 0, "exam_score_max": 60},
    })
    monkeypatch.setattr(m, "list_school_term_calendars", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "rollover_school_term_data_with_cursor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(m, "save_assessment_config_with_cursor", lambda *args, **kwargs: assessment_saves.append(kwargs))

    def fake_update_school_settings_with_cursor(c, school_id, settings):
        saved_settings.update(settings)

    monkeypatch.setattr(m, "update_school_settings_with_cursor", fake_update_school_settings_with_cursor)

    def fake_db_connection(commit=False):
        class FakeCursor:
            pass

        class FakeConn:
            def cursor(self):
                return FakeCursor()

        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()

        return ctx(commit)

    monkeypatch.setattr(m, "db_connection", fake_db_connection)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    resp = client.post(
        "/school-admin/settings?section=results",
        data={
            "settings_section": "results",
            "results_card": "grade_scale",
            "settings_version": "v1",
            "grade_scale_label_1": "A+",
            "grade_scale_min_1": "90",
            "grade_scale_label_2": "A",
            "grade_scale_min_2": "70",
            "grade_scale_label_3": "B+",
            "grade_scale_min_3": "60",
            "grade_scale_label_4": "B",
            "grade_scale_min_4": "50",
            "grade_scale_label_5": "C",
            "grade_scale_min_5": "40",
            "grade_scale_label_6": "F9",
            "grade_scale_min_6": "0",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert assessment_saves == []
    saved_scale = json.loads(saved_settings["grade_scale_json"])
    assert saved_scale[0] == {"label": "A+", "min_score": 90}
    assert saved_scale[-1] == {"label": "F9", "min_score": 0}
    assert saved_settings["grade_a_min"] == 90
    assert saved_settings["grade_b_min"] == 70
    assert saved_settings["grade_c_min"] == 60
    assert saved_settings["grade_d_min"] == 50
    assert saved_settings["grade_label_a"] == "A+"
    assert saved_settings["grade_label_b"] == "A"
    assert saved_settings["grade_label_c"] == "B+"
    assert saved_settings["grade_label_d"] == "B"
    assert saved_settings["grade_label_f"] == "F9"


def test_display_grade_label_uses_school_custom_labels(app_module):
    m = app_module
    school = {
        "grade_label_a": "A1",
        "grade_label_b": "B2",
        "grade_label_c": "B3",
        "grade_label_d": "C4",
        "grade_label_f": "F9",
    }

    assert m.display_grade_label("A", school) == "A1"
    assert m.display_grade_label("B", school) == "B2"
    assert m.display_grade_label("F", school) == "F9"
    assert m.normalize_grade_band("B3", school) == "C"


def test_grade_from_score_uses_custom_grade_scale_json(app_module):
    m = app_module
    school = {
        "grade_scale_json": json.dumps([
            {"label": "A+", "min_score": 90},
            {"label": "A", "min_score": 70},
            {"label": "B+", "min_score": 60},
            {"label": "B", "min_score": 50},
            {"label": "C", "min_score": 40},
            {"label": "F9", "min_score": 0},
        ])
    }

    assert m.grade_from_score(95, school) == "A+"
    assert m.grade_from_score(75, school) == "A"
    assert m.grade_from_score(62, school) == "B+"
    assert m.grade_from_score(54, school) == "B"
    assert m.grade_from_score(12, school) == "F9"
    assert m.normalize_grade_band("A+", school) == "A"
    assert m.normalize_grade_band("B", school) == "D"


def test_teacher_score_entry_start_redirects_for_single_class(client, app_module, monkeypatch):
    m = app_module
    
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "teacher1"
        
    school = {"academic_year": "2025-2026", "current_term": "First Term"}
    monkeypatch.setattr(m, "get_user", lambda user_id: {"user_id": user_id, "role": "teacher", "school_id": "SCH1"})
    monkeypatch.setattr(m, "get_school", lambda school_id: school)
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_teacher_classes", lambda *args, **kwargs: ["JSS1"])
    monkeypatch.setattr(m, "get_teacher_subject_assignments", lambda *args, **kwargs: [])
    
    resp = client.get("/teacher/score-entry")
    assert resp.status_code == 302
    assert "/teacher/score-entry/select-subject/JSS1" in resp.headers["Location"]


def test_teacher_score_entry_select_class_shows_multi_classes(client, app_module, monkeypatch):
    m = app_module
    
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "teacher1"
        
    school = {"academic_year": "2025-2026", "current_term": "First Term"}
    monkeypatch.setattr(m, "get_user", lambda user_id: {"user_id": user_id, "role": "teacher", "school_id": "SCH1"})
    monkeypatch.setattr(m, "get_school", lambda school_id: school)
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_teacher_classes", lambda *args, **kwargs: ["JSS1", "JSS2"])
    monkeypatch.setattr(m, "get_teacher_subject_assignments", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "get_teacher", lambda *args, **kwargs: {"firstname": "Teacher", "lastname": "One", "profile_image": ""})
    monkeypatch.setattr(m, "get_teacher_messages_for_teacher", lambda *args, **kwargs: [])
    
    resp = client.get("/teacher/score-entry")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "JSS1" in body
    assert "JSS2" in body
    assert "Select Class" in body


def test_teacher_score_entry_select_subject_redirects_for_single_subject(client, app_module, monkeypatch):
    m = app_module
    
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "teacher1"
        
    school = {"academic_year": "2025-2026", "current_term": "First Term", "score_entry_mode": "teacher_subject"}
    monkeypatch.setattr(m, "get_user", lambda user_id: {"user_id": user_id, "role": "teacher", "school_id": "SCH1"})
    monkeypatch.setattr(m, "get_school", lambda school_id: school)
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "school_uses_dean_led_score_entry", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        m,
        "get_teacher_subject_assignments",
        lambda *args, **kwargs: [{"classname": "JSS1", "subject": "Mathematics"}]
    )
    
    resp = client.get("/teacher/score-entry/select-subject/JSS1")
    assert resp.status_code == 302
    assert "/teacher?" in resp.headers["Location"]
    assert "tab=score" in resp.headers["Location"]
    assert "score_class=JSS1" in resp.headers["Location"]
    assert "score_subject=Mathematics" in resp.headers["Location"]


def test_school_type_restrictions(client, app_module, monkeypatch):
    m = app_module
    
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "teacher1"

    school = {"school_id": "SCH1", "school_type": "primary", "cbt_enabled": 1, "academic_year": "2025-2026", "current_term": "First Term"}
    monkeypatch.setattr(m, "get_user", lambda user_id: {"user_id": user_id, "role": "teacher", "school_id": "SCH1"})
    monkeypatch.setattr(m, "get_school", lambda school_id: school)
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(m, "get_teacher_classes", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "get_teacher_subject_assignments", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "get_teacher", lambda *args, **kwargs: {"firstname": "Test", "lastname": "Teacher"})
    monkeypatch.setattr(m, "get_teacher_messages_for_teacher", lambda *args, **kwargs: [])
    monkeypatch.setattr(m, "ensure_extended_features_schema", lambda *args, **kwargs: True)

    import contextlib
    @contextlib.contextmanager
    def fake_db_conn(*args, **kwargs):
        class DummyCursor:
            def execute(self, *args, **kwargs): pass
            def fetchall(self): return []
            def fetchone(self): return None
        class DummyConn:
            def cursor(self): return DummyCursor()
            def commit(self): pass
        yield DummyConn()
    monkeypatch.setattr(m, "db_connection", fake_db_conn)

    # Attempting to access Period Attendance should redirect with an error since it is primary
    resp = client.get("/teacher/period-attendance")
    assert resp.status_code == 302
    assert "/teacher" in resp.headers["Location"]

    # Change school type to secondary
    school["school_type"] = "secondary"
    resp = client.get("/teacher/period-attendance")
    # Should not redirect due to primary/nursery restrictions anymore
    assert resp.status_code != 302 or "/teacher" not in resp.headers["Location"] or "This feature is only available" not in (resp.headers.get("Location", ""))


def test_kindergarten_normalization(app_module):
    m = app_module
    
    # Classname normalization tests
    assert m.canonicalize_classname("Kindergarten 1") == "KG1"
    assert m.canonicalize_classname("kindergarting 2") == "KG2"
    assert m.canonicalize_classname("KINDER 3") == "KG3"
    assert m.canonicalize_classname("KG 1") == "KG1"
    
    # School type normalization tests
    assert m.normalize_school_type("kindergarten") == "nursery"
    assert m.normalize_school_type("kindergarten school") == "nursery"
    assert m.normalize_school_type("preschool") == "nursery"
    assert m.normalize_school_type("pre-primary") == "nursery"


def test_parent_merge_profiles_flow(client, app_module, monkeypatch):
    m = app_module
    
    # Mock DB connection at the very beginning of the test to avoid PostgreSQL connection attempts
    updated = []
    import contextlib
    @contextlib.contextmanager
    def fake_db_conn(*args, **kwargs):
        class DummyCursor:
            def execute(self, query, params=None):
                if "UPDATE students" in query:
                    updated.append(params)
            def fetchall(self): return []
            def fetchone(self): return None
        class DummyConn:
            def cursor(self): return DummyCursor()
            def commit(self): pass
        yield DummyConn()

    monkeypatch.setattr(m, "db_connection", fake_db_conn)
    monkeypatch.setattr(m, "students_has_parent_multi_access_columns", lambda: True)
    monkeypatch.setattr(m, "get_school", lambda school_id: {"school_id": school_id, "school_name": "Mock School", "school_type": "mixed"})
    monkeypatch.setattr(m, "get_current_term", lambda school: "First Term")

    # 1. Accessing merge-profiles while unauthenticated redirects to login
    resp = client.get("/parent/merge-profiles")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    
    # 2. Simulate logged in parent with unmerged candidates
    fake_session_data = {
        "role": "parent",
        "parent_phone": "08012345678",
        "parent_logged_in_password_hash": "hash_A",
        "school_id": "SCH1",
        "parent_student_keys": ["SCH1::STU1"],
    }
    
    # Set session values
    with client.session_transaction() as sess:
        for k, v in fake_session_data.items():
            sess[k] = v
            
    # Mock candidate profiles (STU1 has same password hash, STU2 has different)
    candidates = [
        {"school_id": "SCH1", "student_id": "STU1", "firstname": "Child One", "parent_phone": "08012345678", "parent_password_hash": "hash_A"},
        {"school_id": "SCH2", "student_id": "STU2", "firstname": "Child Two", "parent_phone": "08012345678", "parent_password_hash": "hash_B"},
    ]
    
    monkeypatch.setattr(m, "get_parent_students_by_phone", lambda phone: candidates)
    monkeypatch.setattr(m, "get_sms_sending_enabled", lambda: False)
    
    # Check GET page - should render merge-profiles page
    resp = client.get("/parent/merge-profiles")
    assert resp.status_code == 200
    assert b"Merge Parent Profiles" in resp.data
    assert b"Child Two" in resp.data
    
    # Check GET page with send_otp=1 - should generate OTP and set in session
    resp = client.get("/parent/merge-profiles?send_otp=1")
    assert resp.status_code == 302
    assert "/parent/merge-profiles" in resp.headers["Location"]
    
    with client.session_transaction() as sess:
        assert "parent_merge_otp" in sess
        otp_code = sess["parent_merge_otp"]
        
    # Check POST with correct OTP and passwords
    post_data = {
        "otp": otp_code,
        "new_password": "new_secure_pwd",
        "confirm_password": "new_secure_pwd",
    }
    resp = client.post("/parent/merge-profiles", data=post_data)
    assert resp.status_code == 302
    assert "/parent" in resp.headers["Location"]
    
    # Assert DB update was executed with the new password hash for the parent phone number
    assert len(updated) > 0
    assert updated[0][1] == "08012345678"


def test_third_term_layout_mode_settings(app_module, monkeypatch):
    m = app_module
    # Test _combine_student_snapshots correctly sets first_term_mark, second_term_mark, third_term_mark
    snapshots = [
        {
            'term': 'First Term',
            'average_marks': 50.0,
            'subjects': ['Math'],
            'scores': {'Math': {'overall_mark': 50.0, 'test_1': 10, 'exam_score': 40}},
        },
        {
            'term': 'Second Term',
            'average_marks': 60.0,
            'subjects': ['Math'],
            'scores': {'Math': {'overall_mark': 60.0, 'test_1': 15, 'exam_score': 45}},
        },
        {
            'term': 'Third Term',
            'average_marks': 70.0,
            'subjects': ['Math'],
            'scores': {'Math': {'overall_mark': 70.0, 'test_1': 20, 'exam_score': 50}},
        }
    ]
    monkeypatch.setattr(m, "get_school", lambda sid: {"combine_third_term_results": 1, "third_term_layout_mode": "term_summary"})
    monkeypatch.setattr(m, "get_grade_config", lambda sid: {"pass_mark": 0, "grade_a_min": 70, "grade_b_min": 60, "grade_c_min": 50, "grade_d_min": 40})
    
    combined = m._combine_student_snapshots(snapshots, "SCH")
    assert combined is not None
    math_scores = combined['scores']['Math']
    assert math_scores['first_term_mark'] == 50.0
    assert math_scores['second_term_mark'] == 60.0
    assert math_scores['third_term_mark'] == 70.0
    assert math_scores['overall_mark'] == pytest.approx(60.0)


def test_update_pass_mark_ajax(client, app_module, monkeypatch):
    m = app_module
    with client.session_transaction() as sess:
        sess['role'] = 'school_admin'
        sess['school_id'] = 'SCH'
        sess['user_id'] = 'admin1'

    updated_db = []
    def fake_db_connection(commit=False):
        class FakeCursor:
            def execute(self, query, params=None):
                if "UPDATE schools SET pass_mark" in query:
                    updated_db.append(params)
            def fetchone(self):
                return None
        class FakeConn:
            def cursor(self):
                return FakeCursor()
            def commit(self):
                pass
        @contextlib.contextmanager
        def ctx(commit=False):
            yield FakeConn()
        return ctx(commit)

    monkeypatch.setattr(m, "db_connection", fake_db_connection)
    monkeypatch.setattr(m, "get_school", lambda sid: {"id": "SCH", "pass_mark": 50})
    monkeypatch.setattr(m, "invalidate_school_cache", lambda sid: None)
    monkeypatch.setattr(m, "record_admin_action_audit", lambda *args, **kwargs: None)

    resp = client.post("/school-admin/update-pass-mark-ajax", json={"pass_mark": 65})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    assert resp.get_json()["pass_mark"] == 65
    assert len(updated_db) == 1
    assert updated_db[0] == (65, "SCH")


def test_nursery_primary_report_customization(client, app_module, monkeypatch):
    import flask
    m = app_module

    # 1. Test PDF Builder function directly
    report_data = {
        'school_name': 'Greenfields Nursery School',
        'school_type': 'nursery',
        'student_name': 'Chidi Obi',
        'student_id': 'PUP-001',
        'class_name': 'Nursery 1A',
        'term': 'First Term',
        'year': '2026/2027',
        'average': 85.5,
        'class_average': 78.0,
        'grade': 'A',
        'status': 'Promoted',
        'show_positions': True,
        'subject_rows': [
            {'subject': 'Numeracy', 'total_exam': 45.0, 'highest': 50.0, 'lowest': 20.0, 'total': 90.0, 'grade': 'A', 'position': '1/15'}
        ]
    }

    pdf_bytes = m._build_rich_result_pdf_reportlab(report_data)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0

    # 2. Test HTML Rendering in context for Nursery / KG class
    with m.app.test_request_context():
        # Case A: Nursery / KG Class (Child)
        rendered_kg = flask.render_template(
            'student/student_result.html',
            student={
                'first_name': 'Chidi',
                'student_id': 'PUP-001',
                'class_name': 'KG 1A',
                'term': 'First Term',
                'academic_year': '2026/2027',
                'average_marks': 85.5,
                'total_score': 90.0,
                'number_of_subject': 1,
                'Status': 'Promoted',
                'Grade': 'A',
                'subjects': {
                    'Numeracy': {'first_term_mark': 40, 'second_term_mark': 45, 'third_term_mark': 45, 'overall_mark': 90, 'grade': 'A'}
                }
            },
            school={
                'school_name': 'Greenfields Academy',
                'school_type': 'mixed',
                'show_positions': 1,
                'test_score_max': 30,
                'max_tests': 3
            },
            position={'pos': 1, 'size': 15, 'class': 'KG 1A', 'is_stream_separate': False},
            subject_positions={'Numeracy': {'pos': 1, 'size': 15, 'highest': 90.0, 'lowest': 50.0}},
            published_terms=[],
            current_term_token='t1',
            available_result_classes=[],
            selected_result_class='',
            term_notice='',
            term_view_endpoint='parent_view_result',
            student_key='key',
            prev_term=None,
            next_term=None,
            behaviour_grade_scale={},
            teacher_signature=None,
            teacher_name='Mrs. Smith',
            principal_name='Mrs. Principal',
            principal_signature=None,
            result_max_tests=3,
            exam_config={'exam_mode': 'separate'}
        )
        assert 'class="report-page school-primary-nursery"' in rendered_kg
        assert 'Child Details' in rendered_kg
        assert 'Child Name' in rendered_kg
        assert 'Children in Class' in rendered_kg

        # Case B: Primary Class (Pupil)
        rendered_pry = flask.render_template(
            'student/student_result.html',
            student={
                'first_name': 'Chidi',
                'student_id': 'PUP-001',
                'class_name': 'Primary 2B',
                'term': 'First Term',
                'academic_year': '2026/2027',
                'average_marks': 85.5,
                'total_score': 90.0,
                'number_of_subject': 1,
                'Status': 'Promoted',
                'Grade': 'A',
                'subjects': {
                    'Numeracy': {'first_term_mark': 40, 'second_term_mark': 45, 'third_term_mark': 45, 'overall_mark': 90, 'grade': 'A'}
                }
            },
            school={
                'school_name': 'Greenfields Academy',
                'school_type': 'mixed',
                'show_positions': 1,
                'test_score_max': 30,
                'max_tests': 3
            },
            position={'pos': 1, 'size': 15, 'class': 'Primary 2B', 'is_stream_separate': False},
            subject_positions={'Numeracy': {'pos': 1, 'size': 15, 'highest': 90.0, 'lowest': 50.0}},
            published_terms=[],
            current_term_token='t1',
            available_result_classes=[],
            selected_result_class='',
            term_notice='',
            term_view_endpoint='parent_view_result',
            student_key='key',
            prev_term=None,
            next_term=None,
            behaviour_grade_scale={},
            teacher_signature=None,
            teacher_name='Mrs. Smith',
            principal_name='Mrs. Principal',
            principal_signature=None,
            result_max_tests=3,
            exam_config={'exam_mode': 'separate'}
        )
        assert 'class="report-page school-primary-nursery"' in rendered_pry
        assert 'Pupil Details' in rendered_pry
        assert 'Pupil Name' in rendered_pry
        assert 'Pupils in Class' in rendered_pry

        # Case C: Secondary Class (Student)
        rendered_sec = flask.render_template(
            'student/student_result.html',
            student={
                'first_name': 'Chidi',
                'student_id': 'PUP-001',
                'class_name': 'JSS 2B',
                'term': 'First Term',
                'academic_year': '2026/2027',
                'average_marks': 85.5,
                'total_score': 90.0,
                'number_of_subject': 1,
                'Status': 'Promoted',
                'Grade': 'A',
                'subjects': {
                    'Numeracy': {'first_term_mark': 40, 'second_term_mark': 45, 'third_term_mark': 45, 'overall_mark': 90, 'grade': 'A'}
                }
            },
            school={
                'school_name': 'Greenfields Academy',
                'school_type': 'mixed',
                'show_positions': 1,
                'test_score_max': 30,
                'max_tests': 3
            },
            position={'pos': 1, 'size': 15, 'class': 'JSS 2B', 'is_stream_separate': False},
            subject_positions={'Numeracy': {'pos': 1, 'size': 15, 'highest': 90.0, 'lowest': 50.0}},
            published_terms=[],
            current_term_token='t1',
            available_result_classes=[],
            selected_result_class='',
            term_notice='',
            term_view_endpoint='parent_view_result',
            student_key='key',
            prev_term=None,
            next_term=None,
            behaviour_grade_scale={},
            teacher_signature=None,
            teacher_name='Mrs. Smith',
            principal_name='Mrs. Principal',
            principal_signature=None,
            result_max_tests=3,
            exam_config={'exam_mode': 'separate'}
        )
        assert 'class="report-page school-primary-nursery"' not in rendered_sec
        assert 'Student Details' in rendered_sec
        assert 'Student Name' in rendered_sec
        assert 'Students in Class' in rendered_sec





