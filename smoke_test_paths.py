import sys

from student_scor import app


def main():
    cases = [
        ("/", {200}),
        ("/login", {200}),
        ("/terms-privacy", {200}),
        ("/school-admin", {302}),
        ("/teacher", {302}),
        ("/student", {302}),
        ("/school-admin/publish-results", {302}),
        ("/school-admin/add-students-by-class", {302}),
    ]

    failures = []
    with app.test_client() as client:
        for path, allowed in cases:
            resp = client.get(path, follow_redirects=False)
            status = int(resp.status_code or 0)
            ok = status in allowed
            print(f"{path:40} -> {status} {'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append((path, status, sorted(allowed)))

    if failures:
        print("\nSmoke test failures:")
        for path, status, allowed in failures:
            print(f"- {path}: got {status}, expected one of {allowed}")
        return 1
    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
