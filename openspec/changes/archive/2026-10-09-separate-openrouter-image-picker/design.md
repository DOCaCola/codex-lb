# Design

Classify catalog rows by dedicated image metadata. Image-capable entries live in Image models; other entries and unavailable selections live in Models. Reuse the picker and common selection storage. Each save preserves entries outside its scope. Counts reflect each scope, not search results. Read-only and busy controls match existing account actions. Provide a refresh hint when the image catalog is empty; do not infer image capability from a model name. This enables public Images API selections, not a new Codex image backend override.
