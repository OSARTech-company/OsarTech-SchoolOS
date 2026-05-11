"""
Role smoke test for production/staging.

Usage:
  python tools/role_smoke_test.py

Required env for app import (same as normal app startup):
  DATABASE_URL, SECRET_KEY, DEFAULT_STUDENT_PASSWORD, DEFAULT_TEACHER_PASSWORD

Role credentials (set only for roles you want to test):
  SMOKE_SUPER_ADMIN_USERNAME, SMOKE_SUPER_ADMIN_PASSWORD
  SMOKE_SCHOOL_ADMIN_USERNAME, SMOKE_SCHOOL_ADMIN_PASSWORD
  SMOKE_TEACHER_USERNAME, SMOKE_TEACHER_PASSWORD
  SMOKE_STUDENT_USERNAME, SMOKE_STUDENT_PASSWORD
  SMOKE_PARENT_PHONE, SMOKE_PARENT_PASSWORD, SMOKE_PARENT_STUDENT_ID (optional)
"""

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _extract_csrf_token(html_text):
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text or '', re.IGNORECASE)
    return (match.group(1) if match else '').strip()


def _assert_status(resp, expected, label):
    if int(resp.status_code) != int(expected):
        raise RuntimeError(f'{label}: expected HTTP {expected}, got {resp.status_code}')


def _login_via_main_portal(app_module, username, password, expected_prefixes, label, agree_terms=True):
    client = app_module.app.test_client()
    get_login = client.get('/login')
    _assert_status(get_login, 200, f'{label} GET /login')
    token = _extract_csrf_token(get_login.get_data(as_text=True))
    if not token:
        raise RuntimeError(f'{label}: missing csrf_token on /login')
    post_data = {
        'username': (username or '').strip(),
        'password': password or '',
        'csrf_token': token,
    }
    if agree_terms:
        post_data['agree_terms'] = 'on'
    login_resp = client.post('/login', data=post_data, follow_redirects=False)
    if login_resp.status_code not in (302, 303):
        body = (login_resp.get_data(as_text=True) or '')[:240].replace('\n', ' ')
        raise RuntimeError(f'{label}: login failed (HTTP {login_resp.status_code}). Body preview: {body}')
    location = (login_resp.headers.get('Location') or '').strip()
    if not any(location.startswith(pfx) for pfx in expected_prefixes):
        raise RuntimeError(f'{label}: unexpected redirect target after login: {location}')
    follow = client.get(location, follow_redirects=False)
    if follow.status_code not in (200, 302, 303):
        raise RuntimeError(f'{label}: redirected page returned HTTP {follow.status_code}')
    return True


def _login_parent(app_module, phone, password, student_id=''):
    client = app_module.app.test_client()
    get_portal = client.get('/parent-portal')
    _assert_status(get_portal, 200, 'Parent GET /parent-portal')
    token = _extract_csrf_token(get_portal.get_data(as_text=True))
    if not token:
        raise RuntimeError('Parent: missing csrf_token on /parent-portal')
    form = {
        'parent_phone': (phone or '').strip(),
        'password': password or '',
        'student_id': (student_id or '').strip(),
        'csrf_token': token,
    }
    login_resp = client.post('/parent-portal', data=form, follow_redirects=False)
    if login_resp.status_code not in (302, 303):
        body = (login_resp.get_data(as_text=True) or '')[:240].replace('\n', ' ')
        raise RuntimeError(f'Parent: login failed (HTTP {login_resp.status_code}). Body preview: {body}')
    location = (login_resp.headers.get('Location') or '').strip()
    if not location.startswith('/parent'):
        raise RuntimeError(f'Parent: unexpected redirect target after login: {location}')
    follow = client.get(location, follow_redirects=False)
    if follow.status_code not in (200, 302, 303):
        raise RuntimeError(f'Parent: redirected page returned HTTP {follow.status_code}')
    return True


def main():
    import student_scor as app_module

    # Public routes sanity
    public_client = app_module.app.test_client()
    _assert_status(public_client.get('/'), 200, 'GET /')
    _assert_status(public_client.get('/login'), 200, 'GET /login')
    _assert_status(public_client.get('/terms-privacy'), 200, 'GET /terms-privacy')

    checks = []

    sa_user = (os.environ.get('SMOKE_SUPER_ADMIN_USERNAME', '') or os.environ.get('SUPER_ADMIN_USERNAME', '')).strip()
    sa_pass = (os.environ.get('SMOKE_SUPER_ADMIN_PASSWORD', '') or os.environ.get('SUPER_ADMIN_PASSWORD', '')).strip()
    if sa_user and sa_pass:
        _login_via_main_portal(app_module, sa_user, sa_pass, ['/super-admin', '/super-admin/change-password'], 'Super Admin', agree_terms=False)
        checks.append('super_admin')

    sc_user = (os.environ.get('SMOKE_SCHOOL_ADMIN_USERNAME', '') or '').strip()
    sc_pass = (os.environ.get('SMOKE_SCHOOL_ADMIN_PASSWORD', '') or '').strip()
    if sc_user and sc_pass:
        _login_via_main_portal(app_module, sc_user, sc_pass, ['/school-admin', '/school-admin/change-password'], 'School Admin')
        checks.append('school_admin')

    t_user = (os.environ.get('SMOKE_TEACHER_USERNAME', '') or '').strip()
    t_pass = (os.environ.get('SMOKE_TEACHER_PASSWORD', '') or '').strip()
    if t_user and t_pass:
        _login_via_main_portal(app_module, t_user, t_pass, ['/teacher', '/teacher/change-password'], 'Teacher')
        checks.append('teacher')

    st_user = (os.environ.get('SMOKE_STUDENT_USERNAME', '') or '').strip()
    st_pass = (os.environ.get('SMOKE_STUDENT_PASSWORD', '') or '').strip()
    if st_user and st_pass:
        _login_via_main_portal(app_module, st_user, st_pass, ['/student', '/student/change-password'], 'Student')
        checks.append('student')

    p_phone = (os.environ.get('SMOKE_PARENT_PHONE', '') or '').strip()
    p_pass = (os.environ.get('SMOKE_PARENT_PASSWORD', '') or '').strip()
    p_sid = (os.environ.get('SMOKE_PARENT_STUDENT_ID', '') or '').strip()
    if p_phone and p_pass:
        _login_parent(app_module, p_phone, p_pass, p_sid)
        checks.append('parent')

    if not checks:
        print('[WARN] No role credentials provided. Public route checks passed only.')
        return 0

    print('[OK] Smoke test passed for roles: ' + ', '.join(checks))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'[ERROR] Smoke test failed: {exc}', file=sys.stderr)
        raise
