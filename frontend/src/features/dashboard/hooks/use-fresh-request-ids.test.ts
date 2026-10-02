import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useFreshRequestIds } from "@/features/dashboard/hooks/use-fresh-request-ids";
import type { RequestLog } from "@/features/dashboard/schemas";
import { createRequestLogEntry } from "@/test/mocks/factories";

type Props = { requests: readonly RequestLog[]; contextKey: string | null };

const page = (...ids: string[]) => ids.map((requestId) => createRequestLogEntry({ requestId }));

function renderFreshIds(initial: Props) {
  return renderHook(
    ({ requests, contextKey }: Props) => useFreshRequestIds(requests, contextKey),
    { initialProps: initial },
  );
}

describe("useFreshRequestIds", () => {
  it("treats the first result as the baseline", () => {
    const { result } = renderFreshIds({ requests: page("a", "b"), contextKey: "k" });

    expect([...result.current]).toEqual([]);
  });

  it("returns requests that arrive through a refresh of the same context", () => {
    const { result, rerender } = renderFreshIds({ requests: page("b", "c"), contextKey: "k" });

    rerender({ requests: page("a", "b", "d"), contextKey: "k" });

    expect([...result.current].sort()).toEqual(["a", "d"]);
  });

  it("keeps the current arrivals while the request array is unchanged", () => {
    const { result, rerender } = renderFreshIds({ requests: page("b"), contextKey: "k" });
    const refreshed = page("a", "b");
    rerender({ requests: refreshed, contextKey: "k" });

    rerender({ requests: refreshed, contextKey: "k" });

    expect([...result.current]).toEqual(["a"]);
  });

  it("starts a new baseline when the context changes", () => {
    const { result, rerender } = renderFreshIds({ requests: page("a"), contextKey: "k1" });

    rerender({ requests: page("x", "y"), contextKey: "k2" });

    expect([...result.current]).toEqual([]);
  });

  it("ignores untracked data and baselines the next tracked result", () => {
    const { result, rerender } = renderFreshIds({ requests: page("a"), contextKey: "k1" });

    rerender({ requests: page("a"), contextKey: null });
    expect([...result.current]).toEqual([]);

    rerender({ requests: page("x", "y"), contextKey: "k2" });
    expect([...result.current]).toEqual([]);
  });
});
