import importlib
import io
import json

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


def test_school_admin_restore_dry_run_does_not_apply_restore(client, app_module, monkeypatch):
    m = app_module
    called = {"restore": 0, "audit_actions": []}

    monkeypatch.setattr(m, "decrypt_backup_blob", lambda raw, passphrase: raw)
    monkeypatch.setattr(m, "restore_school_backup_payload", lambda *args, **kwargs: called.__setitem__("restore", called["restore"] + 1))
    monkeypatch.setattr(
        m,
        "record_admin_action_audit",
        lambda school_id, action_type, target_scope="", payload=None: called["audit_actions"].append(action_type),
    )

    with client.session_transaction() as sess:
        sess["role"] = "school_admin"
        sess["school_id"] = "SCH1"
        sess["user_id"] = "A1"

    payload = {
        "school": {"school_id": "SCH1", "school_name": "Test"},
        "students": [],
        "teachers": [],
        "parents": [],
        "messages": [],
    }
    data = {
        "mode": "merge",
        "dry_run": "1",
        "backup_file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "backup.json"),
    }
    resp = client.post("/school-admin/restore", data=data, content_type="multipart/form-data", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert called["restore"] == 0
    assert "backup_restore_dry_run" in called["audit_actions"]
