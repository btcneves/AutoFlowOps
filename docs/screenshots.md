# Screenshots

Screenshots are stored in `docs/assets/screenshots/`.

---

## Current Set

These screenshots exist and are referenced in the README.

| Screen | File | Status |
| --- | --- | --- |
| Dashboard | `docs/assets/screenshots/dashboard.png` | ✅ Exists |
| Webhooks | `docs/assets/screenshots/webhooks.png` | ✅ Exists |
| Alerts | `docs/assets/screenshots/alerts.png` | ✅ Exists |
| Reports | `docs/assets/screenshots/reports.png` | ✅ Exists |
| API docs (Swagger) | `docs/assets/screenshots/api-docs.png` | ✅ Exists |

---

## Planned Screenshots (not yet captured)

The following screenshots should be taken once the corresponding frontend pages are implemented.

| Screen | File | Prerequisite |
| --- | --- | --- |
| Jobs list | `docs/assets/screenshots/jobs.png` | Jobs management UI (planned) |
| Job detail + executions | `docs/assets/screenshots/job-detail.png` | Jobs management UI (planned) |
| Execution detail | `docs/assets/screenshots/execution-detail.png` | Executions page (planned) |

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

3. Open `http://localhost:3000` in a browser.

4. Navigate to each page and capture a screenshot at 1440 × 900 px or similar widescreen resolution.

5. Save files to `docs/assets/screenshots/` using the filenames in the table above.

6. Screenshots must be generated from demo data only — never from real operational data or secrets.

---

## Screenshot Guidelines

- Use the demo data seeded by `make seed` — never real tokens, credentials or production data.
- Crop to the main content area; avoid browser chrome or OS decorations.
- Keep file sizes reasonable (PNG, under 500 KB each).
- Retake screenshots after significant UI changes.
