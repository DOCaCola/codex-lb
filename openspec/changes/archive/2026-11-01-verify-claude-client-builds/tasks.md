## 1. Verified builds

- [x] 1.1 Carry the CLI, SDK and runtime versions of one build through the request profile.
- [x] 1.2 Verify new releases from their npm package (integrity hash, binary scan) before adoption.
- [x] 1.3 Store verified builds; ship builds verified at review; reset unverified state in the migration.
- [x] 1.4 Restrict pins to verified builds and list them in the dashboard.

## 2. Verification

- [x] 2.1 Scan the published 2.1.282 and 2.1.316 Linux packages with the scanner.
- [x] 2.2 Cover adoption, failed verification, pins, migration repair and scanner edge cases.
