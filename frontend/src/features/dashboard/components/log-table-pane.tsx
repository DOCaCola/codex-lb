import { useLayoutEffect, type ReactNode, type RefObject, type UIEvent } from "react";

export type LogTablePaneProps = {
  /** The pane's scroll container; callers use it to anchor live arrivals. */
  scrollRef: RefObject<HTMLDivElement | null>;
  /** Identifies the shown page; a new value scrolls the pane back to its first row. */
  scrollKey: string;
  /** Pager row pinned below the scroll region; null when there is nothing to page. */
  footer: ReactNode | null;
  /** Content floating over the top of the scroll region. */
  overlay?: ReactNode;
  onScroll?: (event: UIEvent<HTMLDivElement>) => void;
  children: ReactNode;
};

/**
 * A card that fills the remaining page height and scrolls its rows inside,
 * so paging, page-size changes and live arrivals never change the page height
 * and the pager stays in view.
 */
export function LogTablePane({ scrollRef, scrollKey, footer, overlay, onScroll, children }: LogTablePaneProps) {
  useLayoutEffect(() => {
    const region = scrollRef.current;
    if (region) {
      region.scrollTop = 0;
    }
  }, [scrollKey, scrollRef]);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card">
      {overlay}
      <div
        ref={scrollRef}
        data-testid="log-table-scroll-region"
        className="min-h-0 flex-1 overflow-auto [overflow-anchor:none]"
        onScroll={onScroll}
      >
        {children}
      </div>
      {footer ? <div className="flex shrink-0 justify-end border-t px-3 py-2">{footer}</div> : null}
    </div>
  );
}

/** Header classes for a table inside `LogTablePane`: pinned while rows scroll. */
export const LOG_TABLE_HEADER_CLASS =
  "sticky top-0 z-10 bg-card [&_tr]:border-b-0 [&_th]:shadow-[inset_0_-1px_0_var(--border)]";
