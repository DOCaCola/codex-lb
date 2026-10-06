import { useState } from "react";

import type { RequestLog } from "@/features/dashboard/schemas";

type FreshRequestState = {
  contextKey: string | null;
  requests: readonly RequestLog[] | null;
  fresh: ReadonlySet<number>;
};

const NO_LOG_IDS: ReadonlySet<number> = new Set();

const INITIAL_STATE: FreshRequestState = {
  contextKey: null,
  requests: null,
  fresh: NO_LOG_IDS,
};

/**
 * Returns the row IDs of log entries that arrived through a refresh of an
 * unchanged query context. The first result of each context only establishes
 * the baseline. `contextKey` is null while the shown data does not belong to
 * the current context (placeholder data) or when arrivals should not be shown.
 *
 * `requests` must keep its identity while the data is unchanged (the query's
 * structurally shared array), so unrelated re-renders keep the current set.
 */
export function useFreshLogIds(
  requests: readonly RequestLog[],
  contextKey: string | null,
): ReadonlySet<number> {
  const [state, setState] = useState<FreshRequestState>(INITIAL_STATE);

  if (contextKey === null) {
    return NO_LOG_IDS;
  }
  if (state.requests === requests && state.contextKey === contextKey) {
    return state.fresh;
  }

  let fresh = NO_LOG_IDS;
  if (state.contextKey === contextKey && state.requests) {
    const previousIds = new Set(state.requests.map((request) => request.id));
    const arrived = requests.map((request) => request.id).filter((id) => !previousIds.has(id));
    if (arrived.length > 0) {
      fresh = new Set(arrived);
    }
  }
  setState({ contextKey, requests, fresh });
  return fresh;
}
