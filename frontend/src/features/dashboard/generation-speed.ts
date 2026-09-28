import type { RequestLog } from "./schemas";

export function formatGenerationSpeed(request: RequestLog): string | null {
  if (request.outputTokensRaw == null || request.latencyMs == null || request.latencyFirstTokenMs == null) {
    return null;
  }

  const gatewayMeasured = request.modelSourceKind === "openrouter";
  const outputCount = request.outputTokensRaw - (gatewayMeasured ? 0 : (request.reasoningTokens ?? 0));
  const generationMs = request.latencyMs - request.latencyFirstTokenMs;
  if (outputCount <= 0 || generationMs <= 0) {
    return null;
  }
  if (gatewayMeasured && (request.status !== "ok" || generationMs < 1000)) {
    return null;
  }

  return (gatewayMeasured ? "≈" : "") + (outputCount / (generationMs / 1000)).toFixed(1);
}
