import { useLayoutEffect, useState, type RefObject, type UIEvent } from "react";

type UnseenState = {
  contextKey: string | null;
  freshIds: ReadonlySet<number>;
  count: number;
};

export type ArrivalAnchor = {
  /** Arrived rows inserted above the reader's position and not yet scrolled to. */
  unseenCount: number;
  onScroll: (event: UIEvent<HTMLDivElement>) => void;
  /** Scrolls back to the newest rows. */
  reveal: () => void;
};

/**
 * Keeps the rows a reader is looking at in place when live arrivals are
 * inserted at the top of a scrolled log pane, and counts those arrivals until
 * the reader returns to the top. At the top, arrivals simply appear.
 *
 * Rows must carry `data-log-id`; `freshIds` comes from `useFreshLogIds` with
 * the same `contextKey`.
 */
export function useArrivalAnchor(
  scrollRef: RefObject<HTMLDivElement | null>,
  freshIds: ReadonlySet<number>,
  contextKey: string | null,
): ArrivalAnchor {
  const [atTop, setAtTop] = useState(true);
  const [unseen, setUnseen] = useState<UnseenState>({ contextKey, freshIds, count: 0 });

  let current = unseen;
  if (unseen.contextKey !== contextKey) {
    current = { contextKey, freshIds, count: 0 };
    setUnseen(current);
  } else if (unseen.freshIds !== freshIds) {
    current = { contextKey, freshIds, count: atTop ? 0 : unseen.count + freshIds.size };
    setUnseen(current);
  }

  useLayoutEffect(() => {
    const region = scrollRef.current;
    if (!region || region.scrollTop === 0 || freshIds.size === 0) {
      return;
    }
    let insertedHeight = 0;
    for (const row of region.querySelectorAll<HTMLElement>("[data-log-id]")) {
      if (freshIds.has(Number(row.dataset.logId))) {
        insertedHeight += row.offsetHeight;
      }
    }
    region.scrollTop += insertedHeight;
  }, [freshIds, scrollRef]);

  const onScroll = (event: UIEvent<HTMLDivElement>) => {
    const reachedTop = event.currentTarget.scrollTop === 0;
    setAtTop(reachedTop);
    if (reachedTop) {
      setUnseen((previous) => (previous.count === 0 ? previous : { ...previous, count: 0 }));
    }
  };

  const reveal = () => {
    scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  return { unseenCount: contextKey === null ? 0 : current.count, onScroll, reveal };
}
