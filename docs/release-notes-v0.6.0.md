# Release Notes — v0.6.0

**Release date:** 2026-05-20

---

## Overview

v0.6.0 strengthens the notification system introduced in v0.5.0 with two new channel providers (Slack and Telegram), customisable message templates, multi-step escalation policies, and Fernet-based credential encryption for all channel configurations stored in the database.

---

## New features

### Slack webhook channel

A new `slack_webhook` channel type posts messages to any Slack incoming webhook URL using the Slack attachments format. Severity is colour-coded: red for `error`, amber for `warning`, green for everything else.

### Telegram channel

A new `telegram_message` channel type sends formatted messages to a Telegram chat using the Bot API. The `bot_token` is encrypted at rest and masked in all API responses (`{numeric_prefix}:***`).

### Notification templates

The `notification_templates` table stores per-severity (or catch-all) templates with `title_template` and `body_template` fields. Variables: `{title}`, `{severity}`, `{message}`, `{alert_id}`, `{source_type}`, `{source_id}`.

Template resolution order:
1. Exact match on `severity_filter`
2. Catch-all template (`severity_filter IS NULL`), preferring `is_default=true`
3. Built-in fallback

Manage templates via the API (`/api/notification-templates`) or the new **Templates** page in the frontend.

### Escalation policies

An `EscalationPolicy` groups ordered `EscalationStep` records. Each step names a channel and a delay in minutes:
- **delay\_minutes = 0** → channel is notified immediately when the alert fires
- **delay\_minutes > 0** → an `EscalationEvent` record is created with a future `scheduled_at`; a 60-second APScheduler job dispatches overdue events and cancels them when the alert is resolved or acknowledged

Manage policies via `/api/escalation-policies` or the new **Escalation** page in the frontend.

### Credential encryption at rest

All channel `config_encrypted` values are now stored as Fernet ciphertexts. The encryption key comes from:
1. `NOTIFICATION_ENCRYPTION_KEY` environment variable (recommended for production)
2. Derived from `APP_SECRET_KEY` via SHA-256 (dev/test fallback — logs a WARNING)

Existing plain-JSON records from v0.5.0 are detected by their leading `{` character and handled transparently on read; they are re-encrypted on the next write.

---

## Security

- Slack webhook URLs are masked to `scheme://netloc/***` in all API responses and delivery error messages
- Telegram `bot_token` values are masked to `{numeric_prefix}:***` in API responses; errors from the Telegram API contain `***` in place of the real token
- `NOTIFICATION_ENCRYPTION_KEY` should be set before the first production deployment; rotating the key requires re-saving all existing channels

---

## Migration

This release adds four new tables: `notification_templates`, `escalation_policies`, `escalation_steps`, `escalation_events`. The Alembic migration `a1b2c3d4e5f6` runs automatically on backend startup. No data loss occurs for existing channels; their `config_encrypted` values are still readable as plain JSON until they are next saved.

To generate a new Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add `NOTIFICATION_ENCRYPTION_KEY=<output>` to your `.env` or `.env.production` before starting.

---

## Test coverage

| Suite | Result |
| --- | --- |
| Backend lint (ruff) | Clean |
| Backend tests (pytest) | 172 passing |
| Frontend tests (Vitest) | 57 passing |
| Frontend lint (ESLint) | Clean |
| Frontend TypeScript | No errors |
