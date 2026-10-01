import type { TFunction } from "i18next";

import type { RequestLog } from "@/features/dashboard/schemas";

export function requestOperationLabel(request: RequestLog, t: TFunction): string {
  return t(`dashboard.requests.operations.${request.requestOperation ?? "unknown"}`);
}

export function requestTypeLabel(request: RequestLog, t: TFunction): string {
  const standardOperation = request.requestOperation === "responses" || request.requestOperation === "messages";
  const operation = standardOperation ? "" : requestOperationLabel(request, t);
  const kind = request.requestKind;
  if (kind === "normal" || kind === "count_tokens" || kind === "realtime_live") {
    return operation;
  }
  const workload = t(`dashboard.requests.workloads.${kind === "limit_warmup" ? "warmup" : kind}`);
  if (!operation) {
    return workload;
  }
  return request.requestOperation === kind ? operation : `${operation} · ${workload}`;
}
