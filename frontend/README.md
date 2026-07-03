# Frontend Documentation

This folder contains the server-rendered UI for the Student Score Management System.

## What It Is Built With

- `Flask` for routing and request handling
- `Jinja2` templates for page rendering
- `HTML` for structure
- `CSS` for layout and visual styling
- `JavaScript` for small page behaviors and interactions
- `Font Awesome` for icons

## Important Note

This project does not use a separate frontend framework such as React, Vue, or Angular.
There is no standalone frontend build pipeline. Pages are rendered by the Flask app from
templates in `frontend/templates/`.

## Template Layout

Templates are grouped by role:

- `super/` for super admin pages
- `school/` for school admin pages
- `teacher/` for teacher pages
- `student/` for student pages
- `parent/` for parent pages
- `shared/` for pages used across multiple roles

## Shared Assets

Common styles and scripts live in `static/`:

- `static/css/style.css`
- `static/css/dashboard-pro.css`
- `static/css/dashboard-enhanced.css`
- `static/js/dashboard-menu.js`
- `static/js/dashboard-enhanced.js`
- `static/js/app-assistant.js`

## How Pages Are Usually Built

Most screens follow the same pattern:

1. Include the shared loading overlay.
2. Load the main CSS file for the page type.
3. Render a `container`, `header`, and `card` layout.
4. Use shared form controls and button classes.
5. Add only small page-specific CSS or JavaScript when needed.

## Good Places To Start

- `frontend/templates/shared/login.html`
- `frontend/templates/shared/report_issue.html`
- `frontend/templates/shared/help.html`
- `frontend/templates/school/school_admin_dashboard.html`

## If You Need To Extend The UI

- Reuse the shared card/form/button styles first.
- Keep inline CSS small and page-specific.
- Prefer adding reusable rules to `static/css/dashboard-pro.css` when multiple pages need the same pattern.
- Keep template logic in Jinja minimal and move heavy behavior into the Python route when possible.

## Related Docs

- [`backend/README.md`](../backend/README.md)
- [`USER_GUIDE.md`](../USER_GUIDE.md)
- [`DEPLOYMENT.md`](../DEPLOYMENT.md)
