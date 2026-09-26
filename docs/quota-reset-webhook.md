# Quota reset webhook

Configure the optional webhook in **Settings → Quota reset webhook**. Choose
scheduled and/or unexpected resets, enter a public HTTPS destination, and optionally
set a signing secret. The feature is disabled by default. Use **Test delivery** and
the displayed delivery status to verify the destination.

The [quota-reset-webhook specification](../openspec/specs/quota-reset-webhook/spec.md)
defines the contract; [operational context](../openspec/specs/quota-reset-webhook/context.md)
describes detection limits and delivery behavior.

Example JSON body (percentages represent quota **used**, not remaining):

```json
{
  "schema_version": 1,
  "event_id": "a-unique-event-uuid",
  "type": "quota.reset",
  "kind": "unexpected",
  "provider": "openai",
  "account_id": "opaque-local-account-id",
  "window": "secondary",
  "window_minutes": 10080,
  "used_percent_before": 95,
  "used_percent_after": 0,
  "previous_reset_at": "2026-09-29T12:00:00+00:00",
  "reset_at": "2026-09-29T12:00:00+00:00",
  "observed_at": "2026-09-26T12:00:00+00:00",
  "detected_at": "2026-09-26T12:00:01+00:00"
}
```

Test deliveries use `type: quota.test`. Receivers should deduplicate by `event_id`
and promptly return a 2xx response. A successful response means delivery was
accepted, not that downstream actions completed.

When signing is configured, verify `X-Webhook-Signature` as `sha256=` followed by
the hexadecimal HMAC-SHA256 of `X-Webhook-Timestamp + "." + raw_request_body`,
using the configured secret. Compare signatures in constant time and reject stale
timestamps (for example older than five minutes). Do not parse and reserialize the
JSON before verification. `X-Webhook-Id` matches `event_id`; retries retain the
same event ID/body but receive a fresh timestamp/signature.

URLs and secrets are encrypted at rest and omitted from ordinary settings responses.
Authorized administrators can use **Reveal saved URL** to retrieve the destination
on demand; **Hide saved URL** discards the displayed value. This read is audited and
not cached. The signing secret is never revealed.
Notifications contain no account email, authentication tokens or conversation data.
Only administrators with `security:write` can change settings or enqueue tests.
