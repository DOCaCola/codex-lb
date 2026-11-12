# Support Claude Fable 5.2

## Why

Claude Fable 5.2 is in production use (about 1,400 requests since November 9), but the
per-model Claude capability lists still name only Fable 5.1. CLIProxyAPI measured Claude
Code 2.1.321 (b4e7dbd, 6db7d4b, issue #7386) and found:

- Fable 5.2 is a preserved-thinking model: replayed signed thinking needs the
  `drop_block` prefix binding, as for Fable 5.1.
- Claude Code asks Fable 5.2 and Haiku 5.5 for progress updates
  (`thinking.display: "updates"`), extending the 2.1.280 list we mirror.

Without the binding, a Fable 5.2 continuation whose prefix changed can be rejected instead of
having the stale thinking dropped. Without the display, Codex shows a reasoning summary where
Claude Code shows progress updates.

## What Changes

- Fable 5.2 joins the preserved-thinking models, accepting the binding with adaptive and
  manual thinking like Fable 5.1.
- Fable 5.2 and Haiku 5.5 join the translated progress-update models.
- Fable 5.2 gets maintained token limits (1M context, 128k output) for when discovery omits
  them.

Mythos 5.2 needs no entry: CLIProxyAPI lists it only for per-turn timing betas, which we
don't send. Forced tool choice stays restricted to Opus and Sonnet 5.5.

## Impact

Claude request shaping on the translated and native paths. Pricing is unchanged; Fable 5.2
already has its own price entry.
