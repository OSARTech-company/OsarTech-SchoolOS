import importlib
import hmac
import hashlib

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


def test_verify_payment_webhook_signature(app_module, monkeypatch):
    m = app_module
    body = b'{"school_id":"1","status":"paid"}'
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", "whsec_test_key")
    good_sig = hmac.new(b"whsec_test_key", body, hashlib.sha256).hexdigest()
    assert m.verify_payment_webhook_signature(body, good_sig) is True
    assert m.verify_payment_webhook_signature(body, "bad") is False


def test_onboarding_approved_email_contains_invite_url(app_module, monkeypatch):
    m = app_module
    sent = []

    def fake_send(subject, body_text, recipients):
        sent.append({"subject": subject, "body": body_text, "recipients": recipients})
        return {"sent": len(recipients), "errors": [], "recipients": recipients}

    monkeypatch.setattr(m, "send_plain_email_message", fake_send)
    monkeypatch.setenv("SUPPORT_EMAIL", "support@example.com")
    out = m.send_onboarding_event_notifications(
        "approved",
        {
            "request_id": "REQ-20260308-ABC123",
            "school_name": "Saint Mark College",
            "admin_email": "admin@saintmark.edu",
            "school_email": "info@saintmark.edu",
            "invite_url": "https://example.com/school-admin-invite/token123",
            "review_note": "Approved by test",
        },
        actor_user="superadmin@example.com",
        linked_school_id="12",
        admin_username="admin@saintmark.edu",
    )
    assert out["sent"] >= 1
    assert any("school-admin-invite/token123" in item["body"] for item in sent)


def test_super_admin_2fa_helper_validation(app_module, monkeypatch):
    m = app_module
    monkeypatch.setattr(m, "SUPER_ADMIN_EMAIL_2FA_ENABLED", True)

    def fake_send(_subject, _body, _recipients):
        return {"sent": 1, "errors": [], "recipients": _recipients}

    monkeypatch.setattr(m, "send_plain_email_message", fake_send)

    with m.app.test_request_context("/login"):
        ok = m._begin_super_admin_email_2fa({"username": "superadmin@example.com"}, client_ip="127.0.0.1")
        assert ok is True
        code = m.session.get("super_admin_2fa_code")
        valid, reason = m._super_admin_2fa_is_valid(code, client_ip="127.0.0.1")
        assert valid is True
        assert reason == ""
        invalid, _ = m._super_admin_2fa_is_valid("000000", client_ip="127.0.0.1")
        assert invalid is False


def test_school_onboarding_contact_validation_helpers(app_module):
    m = app_module
    assert m._is_plausible_school_phone("+2348012345678") is True
    assert m._is_plausible_school_phone("08012345678") is True
    assert m._is_plausible_school_phone("12") is False

    assert m._is_generic_public_email_domain("info@school.edu.ng") is False
    assert m._is_generic_public_email_domain("my.school@gmail.com") is True

    h1 = m._hash_school_onboarding_email_code("REQ-1", "info@school.edu.ng", "123456")
    h2 = m._hash_school_onboarding_email_code("REQ-1", "info@school.edu.ng", "123456")
    h3 = m._hash_school_onboarding_email_code("REQ-1", "info@school.edu.ng", "654321")
    assert h1 == h2
    assert h1 != h3
