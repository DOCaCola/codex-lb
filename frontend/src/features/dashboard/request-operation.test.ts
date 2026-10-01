import { describe, expect, it } from "vitest";

import i18n from "@/i18n";
import { requestOperationLabel, requestTypeLabel } from "@/features/dashboard/request-operation";
import type { RequestLog } from "@/features/dashboard/schemas";
import { createRequestLogEntry } from "@/test/mocks/factories";

describe("request operation labels", () => {
  it.each<[RequestLog["requestOperation"], RequestLog["requestKind"], string]>([
    ["responses", "normal", "Responses"],
    ["responses", "warmup", "Responses · Warmup"],
    ["responses", "limit_warmup", "Responses · Warmup"],
    ["responses", "prewarm", "Responses · Prewarm"],
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

  it.each([["ko", "체크포인트 인계"], ["zh-CN", "检查点交接"]])("localizes handoff in %s", (language, expected) => {
    const request = createRequestLogEntry({ requestOperation: "checkpoint_handoff" });
    expect(requestOperationLabel(request, i18n.getFixedT(language))).toBe(expected);
  });
});
