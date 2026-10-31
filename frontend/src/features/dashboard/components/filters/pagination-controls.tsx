import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

type PageWindow = {
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
  onOffsetChange: (offset: number) => void;
};

export type PaginationControlsProps = PageWindow & {
  onLimitChange: (limit: number) => void;
};

function PageRange({ total, limit, offset }: Pick<PageWindow, "total" | "limit" | "offset">) {
  const { t } = useTranslation();
  const rangeStart = total > 0 ? offset + 1 : 0;
  const rangeEnd = Math.min(offset + limit, total);
  return (
    <span className="tabular-nums text-muted-foreground">
      {t("dashboard.pagination.range", { start: rangeStart, end: rangeEnd, total })}
    </span>
  );
}

function StepButtons({ limit, offset, hasMore, onOffsetChange }: Omit<PageWindow, "total">) {
  const { t } = useTranslation();
  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={offset <= 0}
        onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        aria-label={t("dashboard.pagination.previousPage")}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={!hasMore}
        onClick={() => onOffsetChange(offset + limit)}
        aria-label={t("dashboard.pagination.nextPage")}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </>
  );
}

/** Range plus previous/next, for toolbars that sit above a paged list. */
export function CompactPaginationControls(props: PageWindow) {
  return (
    <div className="flex items-center gap-2 text-xs" data-testid="compact-pagination">
      <PageRange {...props} />
      <StepButtons {...props} />
    </div>
  );
}

export function PaginationControls({
  total,
  limit,
  offset,
  hasMore,
  onLimitChange,
  onOffsetChange,
}: PaginationControlsProps) {
  const { t } = useTranslation();
  const lastPage = total > 0 ? Math.max(0, Math.ceil(total / limit) - 1) * limit : 0;

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-muted-foreground">{t("dashboard.pagination.rows")}</span>
      <Select value={String(limit)} onValueChange={(value) => onLimitChange(Number(value))}>
        <SelectTrigger size="sm" className="w-20">
          <SelectValue />
        </SelectTrigger>
        <SelectContent align="end">
          {PAGE_SIZE_OPTIONS.map((size) => (
            <SelectItem key={size} value={String(size)}>
              {size}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <PageRange total={total} limit={limit} offset={offset} />

      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={offset <= 0}
        onClick={() => onOffsetChange(0)}
        aria-label={t("dashboard.pagination.firstPage")}
      >
        <ChevronsLeft className="h-4 w-4" />
      </Button>
      <StepButtons limit={limit} offset={offset} hasMore={hasMore} onOffsetChange={onOffsetChange} />
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={!hasMore}
        onClick={() => onOffsetChange(lastPage)}
        aria-label={t("dashboard.pagination.lastPage")}
      >
        <ChevronsRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
