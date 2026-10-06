import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useFreshLogIds } from "@/features/dashboard/hooks/use-fresh-log-ids";
import type { RequestLog } from "@/features/dashboard/schemas";
import { createRequestLogEntry } from "@/test/mocks/factories";

type Props = { requests: readonly RequestLog[]; contextKey: string | null };

const page = (...ids: number[]) => ids.map((id) => createRequestLogEntry({ id }));

function renderFreshIds(initial: Props) {
  return renderHook(
    ({ requests, contextKey }: Props) => useFreshLogIds(requests, contextKey),
    { initialProps: initial },
  );
}

describe("useFreshLogIds", () => {
  it("treats the first result as the baseline", () => {
    const { result } = renderFreshIds({ requests: page(1, 2), contextKey: "k" });

    expect([...result.current]).toEqual([]);
  });

  it("returns requests that arrive through a refresh of the same context", () => {
    const { result, rerender } = renderFreshIds({ requests: page(2, 3), contextKey: "k" });

    rerender({ requests: page(1, 2, 4), contextKey: "k" });

    expect([...result.current].sort()).toEqual([1, 4]);
  });

  it("tracks log rows that share a request ID separately", () => {
    const first = createRequestLogEntry({ id: 10, requestId: "req_retry" });
    const { result, rerender } = renderFreshIds({ requests: [first], contextKey: "k" });

    const retry = createRequestLogEntry({ id: 11, requestId: "req_retry" });
    rerender({ requests: [retry, first], contextKey: "k" });

    expect([...result.current]).toEqual([11]);
  });

  it("keeps the current arrivals while the request array is unchanged", () => {
    const { result, rerender } = renderFreshIds({ requests: page(2), contextKey: "k" });
    const refreshed = page(1, 2);
    rerender({ requests: refreshed, contextKey: "k" });

    rerender({ requests: refreshed, contextKey: "k" });

    expect([...result.current]).toEqual([1]);
  });

  it("starts a new baseline when the context changes", () => {
    const { result, rerender } = renderFreshIds({ requests: page(1), contextKey: "k1" });

    rerender({ requests: page(7, 8), contextKey: "k2" });

    expect([...result.current]).toEqual([]);
  });

  it("ignores untracked data and baselines the next tracked result", () => {
    const { result, rerender } = renderFreshIds({ requests: page(1), contextKey: "k1" });

    rerender({ requests: page(1), contextKey: null });
    expect([...result.current]).toEqual([]);

    rerender({ requests: page(7, 8), contextKey: "k2" });
    expect([...result.current]).toEqual([]);
  });
});
