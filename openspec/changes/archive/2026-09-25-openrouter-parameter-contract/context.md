# Rationale and verification

OpenRouter parameter support and tool availability are separate facts. Keep strict routing and price-first selection, but omit unsupported permissive parallel hints. An explicit serial constraint must fail clearly rather than be silently weakened. Model-level supported parameters allow routing to compatible endpoints; they do not claim every endpoint supports every parameter.

OpenRouter HTTP errors can use numeric `error.code`. Codex 0.157.0's `WrappedWebsocketError` expects `Option<String>`; a numeric code makes deserialization fail before its HTTP-status handling can terminate the stream. Normalize at the OpenRouter forwarding boundary so HTTP and WebSocket clients receive the same valid envelope. Keep the bridge's existing terminal error frame and reusable connection.

The September 25 production rejection did not retain a request-body archive, so the historical offending parameter cannot be proven. Regression tests reproduce a numeric-code 404 using a stub upstream and verify prompt error delivery and a second turn on the same WebSocket for both Responses endpoints. No production inference was replayed.

Cross-check: OmniRoute's `projectCompletedStreamError` stringifies HTTP status codes. OpenCodex's translated error formatter constructs classified string codes, though its generic WebSocket bridge itself passes error objects through. Both references support provider-boundary normalization rather than closing healthy connections.

After deployment, refresh each OpenRouter account's catalog to reproject stored selections with supported parameters and ascending reasoning choices. Clients must refresh their model catalogs. Existing native OpenAI catalogs and routing remain unchanged. For Qwen efforts `xhigh, medium, low`, clients now receive `low, medium, xhigh`, retaining `xhigh` as default.
