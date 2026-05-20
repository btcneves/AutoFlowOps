# Release Notes — AutoFlowOps v0.5.0

**Release date:** 2026-05-20

---

## Summary

AutoFlowOps v0.5.0 adds external notification channels for critical operational alerts. Teams can now send job and webhook failure alerts to Discord webhooks, SMTP email inboxes or custom HTTP webhooks while keeping channel secrets masked in API responses, UI output and delivery error records.

---

## Main Features

### Notification Channels

- Create, edit, activate, pause, test and delete notification channels
- Supported types: `discord_webhook`, `smtp_email` and `custom_webhook`
- Frontend page added at `/notifications`

### Alert Delivery

- Critical job failure alerts dispatch notifications through all active channels
- Webhook token validation failures and paused webhook deliveries create critical alerts
- Notification sends use a short retry loop and never block alert persistence

### Delivery History

- New delivery records capture channel, alert, status, timestamp and masked error details
- Test sends create delivery records with `alert_id: null`
- API responses return only masked channel configuration

---

## Upgrade Notes

1. Pull the release and rebuild the backend image.
2. Run database migrations with `alembic upgrade head` or start the Docker stack so the backend entrypoint runs migrations automatically.
3. Log in and open **Notification Channels**.
4. Add a Discord webhook, SMTP email or custom webhook channel.
5. Use the channel test action before relying on production alerts.

This release adds two tables:

- `notification_channels`
- `notification_deliveries`

---

## Security Notes

- Channel secrets are masked in API responses and UI output.
- Delivery errors are scrubbed before persistence.
- Custom webhook URLs are checked by the SSRF guard when SSRF protection is enabled.
- Notification credentials must be stored for delivery and are not database-encrypted yet; protect database access and backups accordingly.

---

## Known Limitations

- Slack and Telegram providers are not implemented yet.
- Delivery retry uses a simple short retry loop.
- Advanced templates, escalation policies and RBAC are not included in this release.
- Notification credentials are masked but not encrypted at the database layer.
