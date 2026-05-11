# Student Score App User Guide

## Purpose
This app is used to manage score entry, class result approval, publishing, and result viewing for schools.

## Roles
1. `Super Admin`: manages schools and platform-wide security settings.
2. `School Admin`: manages teachers, class subjects, students, approvals, publishing controls.
3. `Teacher`: enters assigned scores, handles class result submission (if class teacher).
4. `Student/Parent`: views published results only.

## Core Workflow
1. School admin configures class subjects.
2. School admin assigns:
   - class teacher per class/term/year
   - subject teachers per class/term/year
3. Subject teachers enter scores only for assigned subjects.
4. Class teacher confirms completeness and submits class result.
5. School admin approves/rejects.
6. Approved result is published and visible to student/parent.

## Teacher Dashboard (How to read it)
1. `Assignment Overview`:
   - `Class Teacher Assignment`: classes you own for submission workflow.
   - `Subject Teacher Assignment`: subjects/classes you can score.
2. `Subject Score Entry`: quick links per student and assigned subject.
3. `Submit Results for Approval`: only for class-teacher-assigned classes.
4. `Subject Completion Tracker`: readiness check before submission.

## Important Rules
1. You cannot score subjects that are not assigned to you.
2. Class submission is blocked until required class data is complete.
3. Score changes after initial entry may require a reason and are auditable.
4. Published results are treated as controlled output; corrections should be traceable.

## Common User Errors
1. "No subject assignment": school admin has not assigned subjects for your class/term.
2. "Cannot submit": pending subject scores, attendance, or behaviour records.
3. "Cannot view result": result not yet published or access not allowed for your role.

## Best Practice
1. Assign classes and subjects at term start.
2. Keep assignments updated when staff changes.
3. Use approval notes clearly when rejecting.
4. Avoid direct manual DB edits; use app actions for traceability.
