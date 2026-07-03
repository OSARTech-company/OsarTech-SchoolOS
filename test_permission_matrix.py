import importlib

import pytest


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


def test_teacher_cannot_open_school_admin_dashboard(client):
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["user_id"] = "T1"
        sess["school_id"] = "SCH1"
    resp = client.get("/school-admin", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")


def test_school_admin_cannot_open_super_admin_dashboard(client):
    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["user_id"] = "A1"
        sess["school_id"] = "SCH1"
    resp = client.get("/super-admin", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")


def test_parent_cannot_open_view_students(client):
    with client.session_transaction() as sess:
        sess["role"] = "parent"
        sess["user_id"] = "P1"
        sess["school_id"] = "SCH1"
    resp = client.get("/view_students", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")


def test_super_admin_can_open_error_logs_page(client):
    with client.session_transaction() as sess:
        sess["role"] = "super_admin"
        sess["user_id"] = "SA1"
    resp = client.get("/super-admin/error-logs", follow_redirects=False)
    assert resp.status_code == 200


def test_bursar_can_open_bursar_dashboard(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_school", lambda school_id: {"school_id": school_id})
    monkeypatch.setattr(app_module, "get_current_term", lambda school: "First Term")
    monkeypatch.setattr(app_module, "load_students", lambda *args, **kwargs: {})
    monkeypatch.setattr(app_module, "get_school_fee_summary", lambda *args, **kwargs: {})
    monkeypatch.setattr(app_module, "render_template", lambda template, **kwargs: f"RENDERED {template}")
    with client.session_transaction() as sess:
        sess["role"] = "bursar"
        sess["user_id"] = "B1"
        sess["school_id"] = "SCH1"
    resp = client.get("/bursar/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    assert resp.data == b"RENDERED bursar/bursar_dashboard.html"


def test_bursar_cannot_open_school_admin_dashboard(client):
    with client.session_transaction() as sess:
        sess["role"] = "bursar"
        sess["user_id"] = "B1"
        sess["school_id"] = "SCH1"
    resp = client.get("/school-admin", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")


def test_teacher_cannot_open_bursar_dashboard(client):
    with client.session_transaction() as sess:
        sess["role"] = "teacher"
        sess["user_id"] = "T1"
        sess["school_id"] = "SCH1"
    resp = client.get("/bursar/dashboard", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("Location", "").endswith("/login")
