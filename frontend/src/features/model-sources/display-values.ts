import type { ModelSource } from "./schemas";

/** The provider label shown wherever an OpenAI-compatible source appears as an account. */
export const OPENAI_COMPATIBLE_LABEL = "OpenAI-compatible";

/** User-defined sources; Claude and OpenRouter sources belong to their own provider accounts. */
export const isUserDefinedSource = (source: ModelSource) => source.kind === "openai_compatible";

export const modelSourceStatus = (source: ModelSource) => (source.isEnabled ? "active" : "paused");

export function sourceProtocols(source: ModelSource): string[] {
  return [
    source.supportsChatCompletions ? "Chat Completions" : null,
    source.supportsResponses ? "Responses" : null,
    source.supportsAudioTranscriptions ? "Audio transcriptions" : null,
    source.supportsEmbeddings ? "Embeddings" : null,
  ].filter((value): value is string => value !== null);
}

export function modelCountLabel(source: ModelSource): string {
  const count = source.models.length;
  return `${count} ${count === 1 ? "model" : "models"}`;
}
