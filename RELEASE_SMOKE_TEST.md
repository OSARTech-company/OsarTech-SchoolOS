# Release Smoke Test Checklist

## Environment
1. Set `DATABASE_URL` and `SECRET_KEY`.
2. Start app with debug off:
   - PowerShell: `$env:FLASK_DEBUG="0"; python student_scor.py`
3. Run route smoke script:
   - `python smoke_test_paths.py`

## Core Login
1. Login as `super_admin`.
2. Login as school admin for School A.
3. Login as school admin for School B.
4. Login as teacher for School A.
5. Login as student for School A (password must be `password`).

## Multi-School Isolation
1. In School A, add teacher `teacher_a@example.com`.
2. In School B, try adding `teacher_a@example.com`.
   - Expected: blocked with username/account conflict message.
3. In School A, assign a School A teacher to a class.
4. Try assigning a teacher ID not in School A.
   - Expected: blocked with "does not belong to your school".

## Student Enrollment
1. In one class, add two students with the same first name.
   - Expected: both can be added if IDs are unique.
2. Add student with duplicate manual Reg No.
   - Expected: duplicate ID is rejected.
3. Archive one student from class list page and restore.
   - Expected: archived student is hidden from active workflows and can be restored.
4. Use "Reset Class Student Passwords" button on class list page.
   - Expected: active students in selected class get reset to configured default password.

## Teacher Workflow
1. Teacher sees only assigned classes.
2. Enter scores within configured max limits.
3. Attempt score above configured limit.
   - Expected: rejected with validation error.
4. Publish results for one class.
5. Edit score after publish.
   - Expected: blocked until unpublished by flow.
6. On Publish Results page, use "Unlock Edit" for a published class and provide reason.
   - Expected: correction/revert operations allowed during unlock window.
7. Use "Re-Lock Edit".
   - Expected: correction/revert operations blocked again.

## Super Admin Controls
1. Turn School A operations OFF.
2. Verify School A school admin is read-only on POST operations.
3. Verify teacher edit routes blocked for School A.
4. Turn School A operations ON and verify normal access resumes.

## Student Access
1. Student can view only published results.
2. Student cannot change password.
3. Public portal login (`/student-portal`) works with student ID + `password`.

## Basic Data Integrity
1. Delete one school from super admin.
2. Verify related students/teachers/assignments are removed for that school only.
3. Verify other school data remains intact.
