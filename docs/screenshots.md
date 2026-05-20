# Screenshots

Screenshots are stored in `docs/assets/screenshots/`.

---

## Current Set

All screenshots captured from the live stack with demo data at 1440 × 900 px.

| Screen | File | Status |
| --- | --- | --- |
| Login | `docs/assets/screenshots/login.png` | ✅ Exists |
| Dashboard | `docs/assets/screenshots/dashboard.png` | ✅ Exists |
| Jobs list | `docs/assets/screenshots/jobs.png` | ✅ Exists |
| Job detail | `docs/assets/screenshots/job-detail.png` | ✅ Exists |
| Job form (edit) | `docs/assets/screenshots/job-form.png` | ✅ Exists |
| Executions | `docs/assets/screenshots/executions.png` | ✅ Exists |
| Execution detail | `docs/assets/screenshots/execution-detail.png` | ✅ Exists |
| Alerts | `docs/assets/screenshots/alerts.png` | ✅ Exists |
| Webhooks | `docs/assets/screenshots/webhooks.png` | ✅ Exists |
| Notification Channels | `docs/assets/screenshots/notification-channels.png` | ✅ Exists |
| Notification Templates | `docs/assets/screenshots/notification-templates.png` | ✅ Exists |
| Escalation Policies | `docs/assets/screenshots/escalation-policies.png` | ✅ Exists |
| Reports | `docs/assets/screenshots/reports.png` | ✅ Exists |
| Users (admin) | `docs/assets/screenshots/users.png` | ✅ Exists |
| Audit Logs | `docs/assets/screenshots/audit-logs.png` | ✅ Exists |
| API docs (Swagger) | `docs/assets/screenshots/api-docs.png` | ✅ Exists |

---

## How to Regenerate Screenshots

1. Start the stack:

   ```bash
   make up
   ```

2. Seed demo data:

   ```bash
   make seed
   ```

3. Run the capture script:

   ```bash
   node scripts/capture_screenshots.js
   ```

   The script authenticates automatically and captures all pages at 1440 × 900 px.

---

## Screenshot Guidelines

- Use the demo data seeded by `make seed` — never real tokens, credentials or production data.
- Capture at 1440 × 900 px viewport (enforced by the script).
- Keep file sizes reasonable (PNG, under 500 KB each).
- Retake screenshots after significant UI changes.
