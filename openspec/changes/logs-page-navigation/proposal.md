## Why

The Logs page grows and shrinks with its rows. At 25 rows the pager sits below the fold, at 100 rows about 5,500 px
down, and changing pages never returns to the first row. When a page gets shorter the browser clamps the scroll
position, which reads as a jump to the top. Error rows are about twice as tall as other rows and clip their text, and a
page title, a filter card, a cost card and a separate conversation summary push the table further down.

## What Changes

- Remove the Logs page title and subtitle.
- Put both views' controls in one toolbar card: view switch, time range, refresh, a one-line summary (request count and
  cost, or conversation count) and a compact pager; the request-log filters and column controls form its second row.
- Render each view's table in a pane that fills the remaining viewport height, scrolls its rows under a pinned header,
  keeps the full pager in its footer and returns to the first row whenever the page or query changes.
- Cap every request-log cell at two lines; error details become one line with the full text on hover and in details.
- Keep the rows a reader is looking at in place when live arrivals are inserted on a scrolled first page, and offer a
  "N new requests" button that returns to them.
- Replace the conversation summary sentence with the toolbar summary and drop the request-log response's
  `conversation` block, which duplicated `total` and `costCoverage`.

## Impact

- Affected specs: `frontend-architecture`, `query-caching`
- Affected code: `frontend/src/features/logs`, `frontend/src/features/dashboard` (request and conversation tables,
  filters, pager), `frontend/src/components/ui/table.tsx`, translations, `app/modules/request_logs` response schema
