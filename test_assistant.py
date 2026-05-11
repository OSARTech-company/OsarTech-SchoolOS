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


def _set_role_session(client, role="school_admin", school_id="SCH1", user_id="U1"):
    with client.session_transaction() as sess:
        sess["role"] = role
        if school_id is not None:
            sess["school_id"] = school_id
        if user_id is not None:
            sess["user_id"] = user_id


def test_assistant_guide_requires_role(client):
    resp = client.post("/assistant/guide", data={"question": "hello"})
    assert resp.status_code == 403


def test_assistant_guide_empty_question_returns_friendly_error(client, app_module, monkeypatch):
    _set_role_session(client, role="teacher", school_id="SCH1", user_id="T1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": ""})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert "Type your question first" in body["error"]


def test_assistant_guide_too_long_question_returns_422(client, app_module, monkeypatch):
    _set_role_session(client, role="teacher", school_id="SCH1", user_id="T1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": "x" * 1305})
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert "too long" in body["error"].lower()


def test_assistant_guide_rate_limit_returns_429(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (False, 7))
    resp = client.post("/assistant/guide", data={"question": "how do i publish"})
    assert resp.status_code == 429
    body = resp.get_json()
    assert body["ok"] is False
    assert "wait" in body["error"].lower()


def test_assistant_guide_nameerror_returns_fix_snippet(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post(
        "/assistant/guide",
        data={
            "question": "NameError: name 'get_class_assignments_with_names' is not defined",
            "page": "/school-admin/data-integrity",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert "get_class_assignments" in (body.get("fix_snippet") or "")
    assert isinstance(body.get("steps"), list) and len(body["steps"]) >= 2


def test_assistant_guide_known_intent_returns_role_guidance(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": "what is promotion audit used for"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert "promotion" in (body.get("answer") or "").lower()
    assert isinstance(body.get("source_hints"), list)


def test_assistant_guide_gender_required_for_add_student_question(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": "must i select gendre for a student before the student is added"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    answer = (body.get("answer") or "").lower()
    assert "gender" in answer
    assert "required" in answer


def test_assistant_micro_faq_communication_button_school_admin(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": "the communication button is for what"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    answer = (body.get("answer") or "").lower()
    assert "communication" in answer or "messages" in answer


def test_assistant_micro_faq_principal_signature_school_admin(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": "how to upload principal signature"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    answer = (body.get("answer") or "").lower()
    assert "signature" in answer
    steps = " ".join(body.get("steps") or []).lower()
    assert "upload" in steps


def test_assistant_micro_faq_school_admin_teacher_work_boundary(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": "can i do the work of a teacher"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    answer = (body.get("answer") or "").lower()
    assert "role" in answer
    assert ("not directly" in answer) or ("teacher-only" in answer) or ("access is role-based" in answer)


def test_assistant_parses_school_settings_open_days_success_message(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    msg = "School settings updated successfully. First Term (2026-2027) open days: 1 (excluding Saturday and Sunday; mid-term break from School Programs)."
    resp = client.post("/assistant/guide", data={"question": msg})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    answer = (body.get("answer") or "").lower()
    assert "success message" in answer
    assert "open day" in answer
    assert "school programs" in answer
    assert "dashboard" not in answer


def test_assistant_micro_faq_teacher_send_image(client, app_module, monkeypatch):
    _set_role_session(client, role="teacher", school_id="SCH1", user_id="T1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    monkeypatch.setattr(
        app_module,
        "_assistant_get_teacher_scope",
        lambda: {
            "mode": "none",
            "has_class_assignment": False,
            "has_subject_assignment": False,
            "class_assignments": [],
            "subject_assignments_by_class": {},
            "all_scope_classes": [],
            "all_scope_subjects": [],
        },
    )
    resp = client.post("/assistant/guide", data={"question": "can i send image to student as note"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    answer = (body.get("answer") or "").lower()
    assert "yes" in answer
    assert "image" in answer


def test_assistant_guide_low_confidence_includes_clarifier(client, app_module, monkeypatch):
    _set_role_session(client, role="parent", school_id="SCH1", user_id="P1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    resp = client.post("/assistant/guide", data={"question": "zzqv kkkv uunm xxyy"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body.get("next_question")
    assert "?" in body.get("next_question")


def test_assistant_low_confidence_uses_specific_clarifying_question(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    monkeypatch.setattr(app_module, "_assistant_rank_role_topics", lambda *args, **kwargs: [])
    resp = client.post("/assistant/guide", data={"question": "qzxwplm rttvbn cccvvn"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    next_q = str(body.get("next_question") or "")
    assert "?" in next_q
    assert "paste the exact page url" not in next_q.lower()
    assert "which page or workflow" not in next_q.lower()
    assert (
        "add students" in next_q.lower()
        or "class subjects" in next_q.lower()
        or "publish results" in next_q.lower()
        or "messages" in next_q.lower()
    )
    assert isinstance(body.get("steps"), list)
    assert len(body.get("steps")) <= 2


def test_assistant_preferences_route_accepts_valid_mode(client, app_module, monkeypatch):
    _set_role_session(client, role="teacher", school_id="SCH1", user_id="T1")
    monkeypatch.setattr(app_module, "set_assistant_user_preference", lambda **kwargs: True)
    resp = client.post("/assistant/preferences", data={"response_mode": "pidgin"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["response_mode"] == "pidgin"


def test_assistant_memory_clear_requires_role(client):
    resp = client.post("/assistant/memory/clear")
    assert resp.status_code == 403
    body = resp.get_json()
    assert body["ok"] is False


def test_assistant_memory_clear_deletes_user_memory(client, app_module, monkeypatch):
    _set_role_session(client, role="teacher", school_id="SCH1", user_id="T1")
    monkeypatch.setattr(app_module, "clear_assistant_memory", lambda **kwargs: 4)
    resp = client.post("/assistant/memory/clear")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["cleared"] == 4


def test_assistant_guide_uses_memory_and_persists_exchange(client, app_module, monkeypatch):
    _set_role_session(client, role="school_admin", school_id="SCH1", user_id="A1")
    monkeypatch.setattr(app_module, "_rate_limit_consume", lambda *args, **kwargs: (True, 0))
    monkeypatch.setattr(
        app_module,
        "get_assistant_memory_history",
        lambda **kwargs: [
            {"role": "user", "text": "what is promotion audit"},
            {"role": "assistant", "text": "promotion audit tracks promotion history"},
        ],
    )
    captured = {"history": None, "saved": None}

    def fake_build_response(role, question, teacher_scope=None, source_page="", conversation_history=None, response_mode="standard"):
        captured["history"] = list(conversation_history or [])
        return {
            "answer": "Use Monitoring > Promotion Audit.",
            "steps": ["Open Monitoring group.", "Click Promotion Audit."],
            "quick_prompts": [],
            "follow_ups": [],
            "next_question": "Do you want filters by class/year?",
            "links": [],
            "source_hints": [],
            "confidence": 0.9,
            "unresolved": False,
        }

    monkeypatch.setattr(app_module, "_assistant_build_response", fake_build_response)

    def fake_save_exchange(**kwargs):
        captured["saved"] = kwargs
        return True

    monkeypatch.setattr(app_module, "save_assistant_memory_exchange", fake_save_exchange)
    resp = client.post(
        "/assistant/guide",
        data={
            "question": "and what about now",
            "history": '[{"role":"user","text":"where do i add students"}]',
            "page": "/school-admin/analytics",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert captured["history"] is not None
    assert any((row.get("text") or "").startswith("what is promotion audit") for row in captured["history"])
    assert any((row.get("text") or "").startswith("where do i add students") for row in captured["history"])
    assert captured["saved"] is not None
    assert captured["saved"]["question"] == "and what about now"
    assert "Promotion Audit" in (body.get("answer") or "") or "Monitoring" in (body.get("answer") or "")
