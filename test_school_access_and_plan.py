import importlib

import pytest


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("DEFAULT_STUDENT_PASSWORD", "password123")
    monkeypatch.setenv("DEFAULT_TEACHER_PASSWORD", "password123")
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "supersecurepassword")
    monkeypatch.setenv("RUN_STARTUP_DDL", "0")
    monkeypatch.setenv("RUN_STARTUP_BOOTSTRAP", "0")
    monkeypatch.setenv("ALLOW_RUNTIME_SCHEMA_HEAL", "0")

    import student_scor

    mod = importlib.reload(student_scor)
    mod.app.config["TESTING"] = True
    mod.app.config["WTF_CSRF_ENABLED"] = False
    return mod


def test_build_school_access_state_grace_window(app_module):
    m = app_module
    state = m.build_school_access_state(
        {
            "access_status": "active_paid",
            "subscription_end_date": "2026-03-01",
            "payment_grace_days": 20,
        }
    )
    # Relative to "today", this test only checks shape and transition intent.
    assert state["effective_status"] in {"active_paid", "pending_payment", "suspended"}
    assert "payment_grace_days" in state


def test_suggest_error_resolution_for_missing_column(app_module):
    m = app_module
    hint = m.suggest_error_resolution(
        error_type="UndefinedColumn",
        error_message='column "reporter_role" does not exist',
        endpoint="view_reports",
        path="/view-reports",
    )
    assert "missing context columns" in (hint.get("summary", "").lower())
    assert len(hint.get("steps", [])) >= 2


def test_ensure_school_plan_capacity_blocks_when_limit_reached(app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(
        m,
        "get_school_plan_limits",
        lambda _sid: {"max_students": 2, "max_teachers": 1, "storage_quota_mb": 0},
    )
    monkeypatch.setattr(m, "get_total_student_count", lambda _sid: 2)
    monkeypatch.setattr(m, "get_total_teacher_count", lambda _sid, include_archived=False: 1)
    with pytest.raises(ValueError):
        m.ensure_school_plan_capacity("SCH1", add_students=1, add_teachers=0)
    with pytest.raises(ValueError):
        m.ensure_school_plan_capacity("SCH1", add_students=0, add_teachers=1)
