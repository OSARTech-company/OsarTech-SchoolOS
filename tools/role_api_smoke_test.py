import os
import importlib
import sys
from pathlib import Path


def _init_app():
    root_dir = Path(__file__).resolve().parents[1]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    os.environ.setdefault("SECRET_KEY", "x" * 40)
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
    os.environ.setdefault("DEFAULT_STUDENT_PASSWORD", "password123")
    os.environ.setdefault("SUPER_ADMIN_PASSWORD", "supersecurepassword")
    os.environ.setdefault("RUN_STARTUP_DDL", "0")
    os.environ.setdefault("RUN_STARTUP_BOOTSTRAP", "0")
    os.environ.setdefault("ALLOW_RUNTIME_SCHEMA_HEAL", "0")
    import student_scor

    mod = importlib.reload(student_scor)
    mod.app.config["TESTING"] = True
    mod.app.config["WTF_CSRF_ENABLED"] = False
    return mod.app


def _assert_redirect_to_login(resp, path, role_label):
    if resp.status_code not in (301, 302, 303, 307, 308):
        raise AssertionError(f"{role_label} on {path}: expected redirect, got {resp.status_code}")
    location = resp.headers.get("Location", "")
    if "/login" not in location:
        raise AssertionError(f"{role_label} on {path}: expected redirect to /login, got {location}")


def run():
    app = _init_app()
    client = app.test_client()

    protected_routes = [
        ("/school-admin/health", "school_admin"),
        ("/teacher", "teacher"),
        ("/parent", "parent"),
        ("/student", "student"),
        ("/super-admin", "super_admin"),
    ]
    wrong_roles = ["teacher", "parent", "student", "school_admin", "super_admin"]

    for path, expected_role in protected_routes:
        resp = client.get(path, follow_redirects=False)
        _assert_redirect_to_login(resp, path, "anonymous")
        for wrong in wrong_roles:
            if wrong == expected_role:
                continue
            with client.session_transaction() as sess:
                sess["role"] = wrong
                sess["school_id"] = "SCH1"
                sess["user_id"] = "U1"
            resp = client.get(path, follow_redirects=False)
            _assert_redirect_to_login(resp, path, f"role={wrong}")
        with client.session_transaction() as sess:
            sess.clear()

    print("role_api_smoke_test: PASS")


if __name__ == "__main__":
    run()
