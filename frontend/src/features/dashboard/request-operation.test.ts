import { describe, expect, it } from "vitest";

import i18n from "@/i18n";
import { requestOperationLabel, requestTypeLabel } from "@/features/dashboard/request-operation";
import type { RequestLog } from "@/features/dashboard/schemas";
import { createRequestLogEntry } from "@/test/mocks/factories";

describe("request operation labels", () => {
  it.each<[RequestLog["requestOperation"], RequestLog["requestKind"], string]>([
    ["responses", "normal", ""],
    ["messages", "normal", ""],
    ["responses", "warmup", "Warmup"],
    ["responses", "limit_warmup", "Warmup"],
    ["responses", "prewarm", "Prewarm"],
    ["responses", "compaction", "Compaction"],
    ["messages", "warmup", "Warmup"],
    ["messages", "limit_warmup", "Warmup"],
    ["messages", "prewarm", "Prewarm"],
    ["messages", "compaction", "Compaction"],
    ["compaction", "compaction", "Compaction"],
    ["compaction", "normal", "Compaction"],
    ["checkpoint_handoff", "normal", "Checkpoint handoff"],
    ["count_tokens", "count_tokens", "Token count"],
    ["realtime_session", "realtime_live", "Realtime session"],
    [null, "normal", "Unknown"],
    [undefined, "warmup", "Unknown · Warmup"],
  ])("combines %s and %s without duplicating labels", (operation, kind, expected) => {
    const request = createRequestLogEntry({ requestOperation: operation, requestKind: kind });
    expect(requestTypeLabel(request, i18n.getFixedT("en"))).toBe(expected);
  });

  it("uses the supplied translator for operation labels", () => {
    const request = createRequestLogEntry({ requestOperation: "web_search" });
    const t = i18n.getFixedT("en");
    expect(requestOperationLabel(request, t)).toBe(t("dashboard.requests.operations.web_search"));
  });

  it.each(["responses", "messages"] as const)("keeps %s explicit in request details", (operation) => {
    const request = createRequestLogEntry({ requestOperation: operation });
    expect(requestOperationLabel(request, i18n.getFixedT("en"))).toBe(
      operation === "responses" ? "Responses" : "Messages",
    );
    expect(request.requestOperation).toBe(operation);
  });

  it.each([
    "unknown", "chat_completions", "count_tokens", "compaction", "checkpoint_handoff",
    "image_generation", "image_edit", "transcription", "embeddings", "file_create", "file_finalize",
    "web_search", "goal_read", "goal_set", "goal_clear", "memory_summary", "analytics", "safety",
    "identity_keys", "realtime_call", "realtime_session",
  ] as const)("preserves nonstandard operation %s", (operation) => {
    const request = createRequestLogEntry({ requestOperation: operation, requestKind: "normal" });
    expect(requestTypeLabel(request, i18n.getFixedT("en"))).toBe(requestOperationLabel(request, i18n.getFixedT("en")));
    expect(requestTypeLabel(request, i18n.getFixedT("en"))).not.toBe("");
  });

  it.each([["ko", "체크포인트 인계"], ["zh-CN", "检查点交接"]])("localizes handoff in %s", (language, expected) => {
    const request = createRequestLogEntry({ requestOperation: "checkpoint_handoff" });
    expect(requestOperationLabel(request, i18n.getFixedT(language))).toBe(expected);
  });
});
