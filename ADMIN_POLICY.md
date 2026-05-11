# Student Score App Admin Policy (Critical Guidance)

## 1. Governance Objective
Protect result integrity, prevent unauthorized edits, and ensure every high-impact action is attributable.

## 2. Separation of Duties
1. Subject teachers enter assigned subject scores.
2. Class teachers coordinate class completeness and submit.
3. School admin approves/rejects and controls publication.
4. Super admin manages platform-level policy and security.

## 3. Mandatory Operational Controls
1. Configure class subjects before any subject assignment.
2. Use explicit class/subject assignment each term/year.
3. Require reasons for sensitive score overrides.
4. Keep approval and rejection records with notes.
5. Restrict viewing/editing by role and assignment scope.

## 4. Publishing and Correction Policy
1. No publication without approval workflow completion.
2. Unpublish/republish must be controlled by school admin credentials.
3. Any correction after publication must include reason.
4. Corrections must be recorded in audit logs.

## 5. Security and Reliability Baseline
1. Use strong environment secrets (`SECRET_KEY`, admin passwords).
2. Enforce HTTPS and secure session cookie settings in production.
3. Run schema migrations before release; do not depend on emergency runtime healing.
4. Perform backup before major term rollover or bulk imports.
5. Test role boundaries after each release.

## 6. Known Structural Risk
The app currently has large logic concentration in `student_scor.py`. This increases change risk and testing burden.  
Recommended refactor track:
1. split routes by role (`teacher`, `school_admin`, `super_admin`)
2. move DB access into repository/service modules
3. isolate policy checks (assignment, publish, correction) in dedicated functions
4. add focused automated tests for workflow gates and permission checks

## 7. Release Checklist
1. Verify class subject config for all active classes.
2. Verify teacher class and subject assignments for current term/year.
3. Verify signature and approval prerequisites.
4. Verify publication toggles and access controls.
5. Run DB health check and smoke-test critical routes.

## 8. User Communication Standard
Keep messages direct and actionable:
1. What failed.
2. Why it failed.
3. What the user should do next.
