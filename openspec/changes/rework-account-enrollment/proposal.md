# Rework account enrollment

## Why

The add-account chooser treats providers differently. Codex offers sign-in and
file import as two options. Claude and Antigravity each have one combined
"OAuth or file import" dialog with an underlined link, a password-type code
field and errors as a red line. OpenRouter and OpenAI-compatible each sit under
their own heading with the same key icon. The account detail labels the
credential renewal "Reconnect" for Claude and Antigravity, but "Re-authenticate"
for Codex.

Claude reconnect also asks for identity-replacement consent up front: a
"Replace the saved identity if this sign-in differs" checkbox. Operators cannot
see what differs before agreeing. If they leave the box unchecked, a mismatch
rejects the sign-in, and the browser round-trip is lost because the OAuth flow
was already used. This happens routinely when a plan change moves an account
to a new organization.

## What Changes

- **Chooser.** A "Subscriptions" group lists Codex, Claude and Antigravity,
  each with its provider logo and the same two options, "Sign in" and
  "Import file". An "API providers" group lists OpenRouter and
  OpenAI-compatible, using their logos as icons. Codex stays on top.
- **Sign-in.** Claude and Antigravity sign-in use the Codex sign-in stages: a
  details stage, then an authorization stage with the link box, Copy, Refresh
  link, a monospace paste field with Submit, and a waiting line with an expiry
  countdown, then success or error with Try again. The link box, copy button
  and paste field are shared components.
- **Import.** File import is a separate dialog per provider, with one shared
  file area that Codex's multi-file import uses too.
- **Re-authenticate.** On Claude and Antigravity details, a "Re-authenticate"
  button, labelled and iconed like Codex's, opens a menu: "Sign in again" or
  "Import credential file". Its dialogs show the saved identity read-only in
  place of the name field.
- **Identity confirmation.** The checkbox is removed. A Claude reconnect whose
  authenticated identity differs is held server-side for ten minutes:
  credentials are encrypted and bound to the account generation. The response
  is 409 with the mismatch code, a pending ID and a comparison of the saved and
  incoming email, organization and plan. The operator confirms (`POST`) or
  discards (`DELETE`) the pending reconnect. Confirming replaces the identity
  with the held credentials, so no second sign-in is needed. `replaceIdentity`
  is removed from the reconnect and OAuth completion requests.
- **Profile labels.** Claude accounts store the email and organization name
  from Anthropic's profile endpoint, set on enrollment, reconnect and identity
  binding, so operators can see which login is expected.
- **API provider dialogs.** The OpenRouter and OpenAI-compatible dialogs get a
  provider logo in the title and Cancel plus the primary action on the right.

## Impact

- Specs: `claude-accounts`, `frontend-architecture`, `model-source-routing`.
- Backend: Claude reconnect, OAuth completion, identity binding, two new
  endpoints, the `claude_pending_reconnects` table, and the
  `claude_accounts.account_email`/`organization_name` columns.
- Frontend: add-account chooser, Codex OAuth and import dialogs, and the
  Claude, Antigravity, OpenRouter and OpenAI-compatible account controls.
- Antigravity reconnect still requires the same Google subject; a different
  subject is rejected as before.
