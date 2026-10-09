# Merge integration
Reuse the generic series renderer. Codex opts into interpolation for measured
quota series; other providers retain explicit unknown gaps. Normalize equivalent
timestamp instants. Scheduled data remains sparse. Monthly labels stay in the
Codex wrapper. Preserve both published no-op merge revisions and join upstream
20260918 with fork 20260929 through a new no-op revision.
