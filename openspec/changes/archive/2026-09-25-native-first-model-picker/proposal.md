# Native-first model picker

## Why
Codex sorts models by ascending priority, so external models assigned zero appear before native OpenAI models despite being appended to the response.

## What Changes
Assign external catalog entries consecutive priorities after the highest emitted native priority. Preserve native priorities, source ordering, visibility, and routing.

## Impact
Only Codex catalog display priorities change. No configuration, database, or inference changes.
