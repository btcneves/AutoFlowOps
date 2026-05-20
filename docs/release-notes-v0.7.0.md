# Release Notes — v0.7.0

**Released:** 2026-05-20

---

## Overview

v0.7.0 adds role-based access control and a full audit trail, making AutoFlowOps suitable for small teams where different members need different levels of access and where a history of sensitive operations is required for accountability.

---

## What's New

### Role-Based Access Control

Three roles are now enforced server-side on every endpoint:

| Role | Who it's for |
| --- | --- |
| `admin` | Full access — user management, audit logs, all configuration |
| `operator` | Day-to-day work — create/run jobs, manage webhooks, ack alerts, test channels, generate reports |
| `viewer` | Read-only visibility into all domain data |

Role checks use FastAPI dependency injection (`require_admin`, `require_operator`) applied per-endpoint. The frontend reflects these boundaries through `AdminRoute` (blocks non-admins from `/users` and `/audit-logs`) and computed `isAdmin`/`isOperator` booleans in `AuthContext`.

### User Management

Admins can now manage all user accounts through the UI or API:

- **List users** — `GET /api/users`
- **Create user** — `POST /api/users` (sets email, name, password, role)
- **Update user** — `PATCH /api/users/{id}` (role, active status, name)
- **Reset password** — `POST /api/users/{id}/reset-password`
- **Delete user** — `DELETE /api/users/{id}`

Self-protection: the API refuses to deactivate or delete the last active admin account.

The **Users** page in the frontend provides all of the above through a table with inline controls.

### Audit Log

Every sensitive action now produces an audit record in the `audit_logs` database table. Each record captures:

- Who performed the action (`user_id`, nullable for failed logins)
- What was done (`action` — e.g. `job.create`, `auth.login_failure`)
- What resource was affected (`resource_type`, `resource_id`)
- Whether it succeeded (`status`)
- Where the request came from (`ip_address`, `user_agent`)
- Additional context (`metadata`) — with sensitive fields replaced by `"[redacted]"`

Admins can view and filter the log at `GET /api/audit-logs` (filters: `user_id`, `action`, `resource_type`, `status`, `since`, `until`, `limit`) or through the **Audit Logs** page in the frontend.

### Audit Coverage

The following actions are logged automatically:

- `auth.login_success` / `auth.login_failure`
- `job.create` / `job.update` / `job.delete` / `job.run`
- `webhook.create` / `webhook.update` / `webhook.delete` / `webhook.reprocess`
- `alert.acknowledge` / `alert.resolve`
- `notification_channel.create` / `.update` / `.delete` / `.activate` / `.deactivate` / `.test`
- `notification_template.create` / `.update` / `.delete`
- `escalation_policy.create` / `.update` / `.delete` / `.add_step` / `.delete_step`
- `report.generate`
- `user.create` / `user.update` / `user.delete` / `user.reset_password`

### Last Login Tracking

The `users` table now records `last_login_at`, updated on every successful login. This is visible in the Users page.

---

## Frontend Changes

- **Users page** (`/users`) — admin-only; user table with name, email, role selector, status badge, last login, created date; inline password reset form; activate/deactivate; delete
- **Audit Logs page** (`/audit-logs`) — admin-only; filter controls for action, resource type, status and date range; paginated log table showing timestamp, actor, action, resource, status and IP
- **Sidebar** — Users and Audit Logs navigation items visible only to admins; role label shown in the footer for the signed-in user
- **`AdminRoute`** — route guard that redirects non-authenticated users to `/login` and authenticated non-admins to `/`

---

## Test Coverage

| Suite | Tests | Status |
| --- | --- | --- |
| RBAC tests (backend) | 20 | Passing |
| Audit log tests (backend) | 5 | Passing |
| User management tests (backend) | 9 | Passing |
| UsersPage tests (frontend) | 4 | Passing |
| AuditLogsPage tests (frontend) | 4 | Passing |
| **Total backend** | **209** | **Passing** |
| **Total frontend** | **65** | **Passing** |

---

## Migration Notes

### New table: `audit_logs`

The `audit_logs` table is created automatically by `Base.metadata.create_all` on backend startup. No manual step is required for fresh deployments.

### New column: `users.last_login_at`

`create_all` does not add columns to existing tables. If upgrading an existing deployment without Alembic:

```sql
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ;
```

Run this against your PostgreSQL database before starting the new backend version.

### Default role change

New users created via `POST /api/users` default to `"viewer"`. If your deployment previously relied on the internal `"user"` role string, update any references to use `"viewer"`.

---

## Upgrade Steps

1. Pull the new image or rebuild: `docker compose build`
2. If upgrading an existing database, run the `ALTER TABLE` statement above.
3. Start services: `docker compose up -d`
4. Log in as admin, verify the Users and Audit Logs pages are accessible.
5. Create an `operator` account for day-to-day work if desired.
6. Verify audit log entries appear after performing a sensitive action.

---

## Known Limitations

- The audit log is append-only **by convention**. Direct database access bypasses the trail.
- `last_login_at` requires a manual `ALTER TABLE` on existing deployments (see above).
- JWT tokens issued before this upgrade remain valid until expiry; no token invalidation is performed during upgrade.
