# Proposal

## Why

Claude requests currently lose cache-write and timing observations, catalog rows lack API-equivalent prices, and budget-thinking models are advertised as non-reasoning. Request logs consequently understate or mislabel usage and costs.

## What Changes

- Preserve inclusive token usage and provider-reported cache/reasoning detail across native and translated Claude responses.
- Record semantic first-output and total upstream-attempt timing using the shared source observation contract.
- Resolve Claude API-equivalent pricing through the existing catalog machinery, keeping unknown distinct from free.
- Advertise and translate model-specific adaptive or budget reasoning without overriding an explicit output limit.
- Display token breakdown independently from monetary availability.
- Carry request-level cost coverage through reports, conversations and API-key usage views, labeling known subtotals when coverage is incomplete.

## Non-goals

No live OAuth calls, deployment, retroactive inference of missing historical usage/timing, or claim that API-equivalent estimates equal subscription charges.
