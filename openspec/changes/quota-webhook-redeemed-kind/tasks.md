## 1. Detection

- [x] 1.1 Relabel an unexpected reset as redeemed when a redemption falls between the baseline and the new observation.
- [x] 1.2 Record redemptions from the usage-limit and banked-credit consume paths before the upstream call.
- [x] 1.3 Migrate the redemption marker and add redeemed to configurations that select unexpected resets.

## 2. Settings

- [x] 2.1 Add the redeemed kind to the webhook filters and default selection.

## 3. Verification

- [x] 3.1 Cover redeemed, earlier-redemption and filtered-out cases, and the consume-path marker.
