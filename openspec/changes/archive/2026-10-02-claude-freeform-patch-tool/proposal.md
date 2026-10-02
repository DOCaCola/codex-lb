## Why
Codex registers its file-editing `apply_patch` tool only for catalog models that advertise `apply_patch_tool_type`. Current Codex has a single patch type, `freeform`, declared as a custom tool with a Lark grammar. Claude models advertise no patch type and the Claude adapter rejects grammar-format custom tools, so Codex sessions on Claude edit files through shell heredocs.

## What Changes
Claude catalog models advertise `apply_patch_tool_type: "freeform"`. The Claude adapter projects grammar-format custom tools as a single raw-text `input` whose schema description carries the declared grammar; the grammar is documented guidance because Anthropic cannot constrain tool decoding. Codex keeps validation authority: it parses every freeform input and returns a non-conforming one to the model as a tool error. Calls round-trip as `custom_tool_call`. Malformed grammar declarations and unknown custom formats remain explicit errors.

References: CLIProxyAPI bridges the same tool to Claude with the grammar in the description (opt-in default introduced 2026-10-02; issue #6286 confirms the default-off catalog behaviour is a bug); opencodex lowers freeform tools to a string `input` and advertises `freeform` by default.

## Capabilities
### Modified Capabilities
- `claude-accounts`: Codex protocol adaptation of grammar-format custom tools and patch-tool catalog advertisement.

## Impact
Claude protocol projection and model-source catalog only. No storage, routing or pricing changes. OpenRouter and OpenAI-compatible sources are unchanged.
