## Decisions

Preserve native feature negotiation. Generate only betas required by deliberate
translated features; effort does not imply tool or thinking capabilities.
Native request IDs/retry metadata belong to the caller; RequestProfile.request_id
remains the independent gateway attempt ID. Transport owns compression negotiation.

Project recognized JSON session metadata using the same account/scope/conversation
identity as the header, including parent-session references. Preserve unrelated
metadata and logical input. Opaque user IDs cannot safely be reinterpreted and
must be rejected when supplied to this OAuth path. Do not invent account UUIDs.

Native helper recognition is compatibility classification, not authentication:
require the native CLI software signals plus structured session identity and a
bounded probe/title shape. Count-token calls may omit main system identity.
Keep endpoint defaults separate; no inferred full-agent beta on native helpers.

## Evidence and qualification

OmniRoute #3415/#9505 demonstrate why unwanted beta activation and discarded
negotiation are dangerous. CLIProxyAPI #6096 preserves native agent/compaction
hints and aligns session identity. Sub2API synchronizes header/body policy.
These precedents do not prove TLS impersonation or every SDK field is required.
Fixtures qualify our forwarding contract, not live OAuth eligibility or billing.
