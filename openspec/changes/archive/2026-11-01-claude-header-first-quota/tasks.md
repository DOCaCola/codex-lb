## 1. Refresh cadence

- [x] 1.1 Schedule usage reads only when header and endpoint evidence is older than 15 minutes, or the last usage read is an hour old.
- [x] 1.2 Bind 429 cooldowns to the credential generation that received them; default retry five minutes.
- [x] 1.3 Keep quota evidence fresh for 30 minutes.

## 2. Header evidence

- [x] 2.1 Record the `7d_oi` window and `overage-in-use` from reply headers.
- [x] 2.2 Read the Fable `weekly_scoped` limit from usage responses into the same window.
- [x] 2.3 Apply the window to Fable models, quota history and trends.
- [x] 2.4 Show the extra-usage badge when a newer reply reports overage in use.

## 3. Dashboard

- [x] 3.1 Accept and label the Weekly Fable window.

## 4. Verification

- [x] 4.1 Cover cadence, generation-bound rate limits, header parsing, endpoint mapping, routing and presentation.
