# Context

## Design decisions

- **List and detail as separate routes.** The pool is compared in the table; one account is configured on its own
  page. Addressable detail pages let Logs and the dashboard link straight to an account.
- **One detail frame for every provider.** Header, banner, menu and the main/side card columns come from one
  component; providers only supply their cards. Settings keep their controls and moved as follows:
  quota rows to the table meters and rail; warm-up state to the Routing column and the Routing card; OpenRouter
  "Used today" to Detailed metrics; model-source protocols and base URL to the Connection card; token status to its own
  card; monitoring to "Sign-in & monitoring" or "API keys"; provider capacity and version settings to the Routing
  card; export and delete to the ⋯ menu; Claude "Refresh" is named "Check limits".
- **Coarse status filter.** The fine-grained status select becomes All / Needs attention / Paused. Re-auth required,
  deactivated, limited and stale-monitoring accounts all count as needing attention.
- **Row menu stays read-only.** Table rows offer Open, Open in Logs and Copy ID. Pausing and limit checks happen on
  the detail page, where the account's state is visible.
- **Rail height.** The rail is sticky below the header; its height leaves room for the breadcrumb above it before the
  page scrolls and for the fixed status bar below it.
