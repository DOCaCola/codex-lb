import { useState } from "react";

import type { RequestLog } from "@/features/dashboard/schemas";

type FreshRequestState = {
  contextKey: string | null;
  requests: readonly RequestLog[] | null;
  fresh: ReadonlySet<string>;
};

const NO_REQUEST_IDS: ReadonlySet<string> = new Set();

const INITIAL_STATE: FreshRequestState = {
  contextKey: null,
  requests: null,
  fresh: NO_REQUEST_IDS,
};

/**
 * Returns the IDs of requests that arrived through a refresh of an unchanged
 * query context. The first result of each context only establishes the
 * baseline. `contextKey` is null while the shown data does not belong to the
 * current context (placeholder data) or when arrivals should not be shown.
 *
 * `requests` must keep its identity while the data is unchanged (the query's
 * structurally shared array), so unrelated re-renders keep the current set.
 */
export function useFreshRequestIds(
  requests: readonly RequestLog[],
  contextKey: string | null,
): ReadonlySet<string> {
  const [state, setState] = useState<FreshRequestState>(INITIAL_STATE);

  if (contextKey === null) {
    return NO_REQUEST_IDS;
  }
  if (state.requests === requests && state.contextKey === contextKey) {
    return state.fresh;
  }

  let fresh = NO_REQUEST_IDS;
  if (state.contextKey === contextKey && state.requests) {
    const previousIds = new Set(state.requests.map((request) => request.requestId));
    const arrived = requests
      .map((request) => request.requestId)
      .filter((requestId) => !previousIds.has(requestId));
    if (arrived.length > 0) {
      fresh = new Set(arrived);
    }
  }
  setState({ contextKey, requests, fresh });
  return fresh;
}
