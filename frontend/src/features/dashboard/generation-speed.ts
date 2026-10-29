import type { RequestLog } from "./schemas";

/** Gateways whose streams codex-lb translates; their speed is measured at the gateway. */
const GATEWAY_KINDS = new Set(["openrouter", "claude", "antigravity"]);

export function isGatewayMeasuredSpeed(request: RequestLog): boolean {
  return request.modelSourceKind != null && GATEWAY_KINDS.has(request.modelSourceKind);
}

export function formatGenerationSpeed(request: RequestLog): string | null {
  if (request.outputTokensRaw == null || request.latencyMs == null || request.latencyFirstTokenMs == null) {
    return null;
  }

  const gatewayMeasured = isGatewayMeasuredSpeed(request);
  const outputCount = request.outputTokensRaw - (gatewayMeasured ? 0 : (request.reasoningTokens ?? 0));
  // Generation ends at the upstream terminal; latencyMs also spans delivery and
  // settlement. Rows logged before the terminal was stored only have latencyMs.
  const generationMs = (request.latencyUpstreamTerminalMs ?? request.latencyMs) - request.latencyFirstTokenMs;
  if (outputCount <= 0 || generationMs <= 0) {
    return null;
  }
  if (gatewayMeasured && (request.status !== "ok" || request.latencyFirstTokenMs < 0 || generationMs < 1000)) {
    return null;
  }

  return (gatewayMeasured ? "≈" : "") + (outputCount / (generationMs / 1000)).toFixed(1);
}
