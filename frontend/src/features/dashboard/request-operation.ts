import type { TFunction } from "i18next";

import type { RequestLog } from "@/features/dashboard/schemas";

type OperationFields = Pick<RequestLog, "requestOperation" | "requestKind">;

export function requestOperationLabel(request: Pick<RequestLog, "requestOperation">, t: TFunction): string {
  return t(`dashboard.requests.operations.${request.requestOperation ?? "unknown"}`);
}

export function requestTypeLabel(request: OperationFields, t: TFunction): string {
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
