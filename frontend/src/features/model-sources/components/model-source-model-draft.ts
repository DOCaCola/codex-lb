import { useState } from "react";
import type {
  ModelSource,
  ModelSourceModelInput,
} from "@/features/model-sources/schemas";
import {
  draftFromSource,
  initialModelSourceDraft,
  mergeReasoningMetadata,
  type ModelSourceDraft,
} from "./model-source-form";
export type ModelRow = {
  key: string;
  model: string;
  displayName: string;
  isEnabled: boolean;
  draft: ModelSourceDraft;
  initialDraft: ModelSourceDraft;
  rawMetadataJson: string | null;
};

export function newRow(): ModelRow {
  return {
    key: crypto.randomUUID(),
    model: "",
    displayName: "",
    isEnabled: true,
    draft: { ...initialModelSourceDraft },
    initialDraft: { ...initialModelSourceDraft },
    rawMetadataJson: null,
  };
}

export function useModelRows(source?: ModelSource) {
  return useState<ModelRow[]>(() =>
    source
      ? source.models.map((model) => {
          const draft = draftFromSource({ ...source, models: [model] });
          return {
            key: String(model.id),
            model: model.model,
            displayName: model.displayName ?? "",
            isEnabled: model.isEnabled,
            draft,
            initialDraft: draft,
            rawMetadataJson: model.rawMetadataJson,
          };
        })
      : [newRow()],
  );
}

export function validateModelRows(rows: ModelRow[]): boolean {
  const ids = rows.map((row) => row.model.trim());
  if (!ids.length || new Set(ids).size !== ids.length) return false;
  return rows.every((row) => {
    if (
      !row.model.trim() ||
      row.model.trim().length > 255 ||
      /[,\n]/.test(row.model) ||
      row.displayName.length > 255
    )
      return false;
    for (const key of ["contextWindow", "maxOutputTokens"] as const) {
      const value = row.draft[key].trim();
      if (value && (!Number.isSafeInteger(Number(value)) || Number(value) <= 0))
        return false;
    }
    for (const key of [
      "inputPer1M",
      "cachedInputPer1M",
      "outputPer1M",
      "audioPerMinute",
    ] as const) {
      const value = row.draft[key].trim();
      if (value && (!Number.isFinite(Number(value)) || Number(value) < 0))
        return false;
    }
    return true;
  });
}

export function modelRowsToInputs(rows: ModelRow[]): ModelSourceModelInput[] {
  return rows.map((row) => {
    const reasoningChanged =
      row.draft.supportsReasoning !== row.initialDraft.supportsReasoning ||
      JSON.stringify(row.draft.reasoningEfforts) !==
        JSON.stringify(row.initialDraft.reasoningEfforts) ||
      row.draft.defaultReasoningEffort !==
        row.initialDraft.defaultReasoningEffort;
    return {
      model: row.model.trim(),
      supportsStreaming: row.draft.supportsStreaming,
      supportsTools: row.draft.supportsTools,
      supportsVision: row.draft.supportsVision,
      displayName: row.displayName.trim() || null,
      isEnabled: row.isEnabled,
      contextWindow: row.draft.contextWindow.trim()
        ? Number(row.draft.contextWindow)
        : null,
      maxOutputTokens: row.draft.maxOutputTokens.trim()
        ? Number(row.draft.maxOutputTokens)
        : null,
      inputPer1M: row.draft.inputPer1M.trim()
        ? Number(row.draft.inputPer1M)
        : null,
      cachedInputPer1M: row.draft.cachedInputPer1M.trim()
        ? Number(row.draft.cachedInputPer1M)
        : null,
      outputPer1M: row.draft.outputPer1M.trim()
        ? Number(row.draft.outputPer1M)
        : null,
      audioPerMinute: row.draft.audioPerMinute.trim()
        ? Number(row.draft.audioPerMinute)
        : null,
      rawMetadataJson: reasoningChanged
        ? mergeReasoningMetadata(
            row.rawMetadataJson,
            row.draft.supportsReasoning,
            row.draft.reasoningEfforts,
            row.draft.defaultReasoningEffort,
          )
        : row.rawMetadataJson,
    };
  });
}
