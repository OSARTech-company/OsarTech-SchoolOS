import importlib

import pytest


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("DEFAULT_STUDENT_PASSWORD", "password123")
    monkeypatch.setenv("DEFAULT_TEACHER_PASSWORD", "teacherpass123")
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "supersecurepassword")
    monkeypatch.setenv("RUN_STARTUP_DDL", "0")
    monkeypatch.setenv("RUN_STARTUP_BOOTSTRAP", "0")
    monkeypatch.setenv("ALLOW_RUNTIME_SCHEMA_HEAL", "0")
    import student_scor

    mod = importlib.reload(student_scor)
    mod.app.config["TESTING"] = True
    mod.app.config["WTF_CSRF_ENABLED"] = False
    # Keep request guards deterministic without a live DB.
    monkeypatch.setattr(
        mod,
        "get_school",
        lambda sid: {
            "school_id": sid,
            "operations_enabled": 1,
            "teacher_operations_enabled": 1,
            "access_status": "trial_free",
        },
    )
    monkeypatch.setattr(
        mod,
        "build_school_access_state",
        lambda school: {"is_allowed": True, "effective_status": "trial_free", "message": ""},
    )
    return mod


@pytest.fixture
def client(app_module):
    return app_module.app.test_client()


def test_cross_role_namespace_redirects_to_login(client):
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["user_id"] = "T1"
        sess["school_id"] = "SCH1"
    resp = client.get("/school-admin", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")


def test_session_binding_mismatch_blocks_access(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_user",
        lambda username: {"username": username, "role": "school_admin", "school_id": "SCH1"},
    )
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["user_id"] = "T1"
        sess["school_id"] = "SCH1"
    resp = client.get("/teacher/messages", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")


def test_mutation_school_scope_mismatch_blocks(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_user",
        lambda username: {"username": username, "role": "school_admin", "school_id": "SCH1"},
    )
    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["user_id"] = "A1"
        sess["school_id"] = "SCH1"
    resp = client.post(
        "/school-admin/assign-teacher",
        data={"teacher_id": "T1", "classname": "SS1", "term": "First Term", "school_id": "SCH2"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")


def test_toggle_operations_records_action_audit(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_user",
        lambda username: {"username": username, "role": "school_admin", "school_id": "SCH1"},
    )
    called = {"toggle": None, "audit": None}

    def _fake_toggle(school_id, enabled):
        called["toggle"] = (school_id, enabled)

    def _fake_audit(school_id, action_type, target_scope="", payload=None):
        called["audit"] = (school_id, action_type, target_scope, payload or {})

    monkeypatch.setattr(app_module, "set_teacher_operations_enabled", _fake_toggle)
    monkeypatch.setattr(app_module, "record_admin_action_audit", _fake_audit)

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["user_id"] = "A1"
        sess["school_id"] = "SCH1"

    resp = client.post("/school-admin/toggle-operations", data={"teacher_operations_enabled": "0"}, follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/school-admin")
    assert called["toggle"] == ("SCH1", False)
    assert called["audit"] is not None
    assert called["audit"][0] == "SCH1"
    assert called["audit"][1] == "toggle_teacher_operations"
