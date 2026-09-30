import type { ComponentProps, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function AccountCardSurface({
  title,
  subtitle,
  description,
  descriptionTitle,
  status,
  actions,
  children,
  className,
  ...props
}: Omit<ComponentProps<"div">, "title"> & {
  title: ReactNode;
  subtitle: ReactNode;
  description?: ReactNode;
  descriptionTitle?: string;
  status: ReactNode;
  actions: ReactNode;
}) {
  return (
    <div
      className={cn(
        "card-hover flex h-full min-w-0 w-full flex-col rounded-xl border bg-card p-4",
        className,
      )}
      {...props}
    >
      <div
        data-slot="account-card-header"
        className="flex min-h-14 items-start justify-between gap-3"
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold leading-tight">
            {title}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {subtitle}
          </p>
          {description ? (
            <p
              className="mt-0.5 truncate text-xs text-muted-foreground"
              title={descriptionTitle}
            >
              {description}
            </p>
          ) : null}
        </div>
        <div className="shrink-0">{status}</div>
      </div>
      <div
        data-slot="account-card-body"
        className="mt-3.5 min-w-0 flex-1 space-y-3"
      >
        {children}
      </div>
      <div
        data-slot="account-card-actions"
        className="mt-3 flex flex-wrap items-center gap-1.5 border-t pt-3"
      >
        {actions}
      </div>
    </div>
  );
}

export function AccountCardAction({
  className,
  ...props
}: ComponentProps<typeof Button>) {
  return (
    <Button
      size="sm"
      variant="ghost"
      className={cn(
        "h-7 gap-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function AccountCardNotice({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "flex min-w-0 items-center justify-between gap-2 rounded-lg bg-muted/40 px-2.5 py-2 text-xs",
        className,
      )}
      {...props}
    />
  );
}

export function AccountSelectionSurface({
  selected,
  className,
  ...props
}: ComponentProps<"button"> & { selected: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(
        "relative min-w-0 w-full rounded-lg px-3 py-2.5 text-left transition-colors",
        selected ? "bg-primary/8 ring-1 ring-primary/25" : "hover:bg-muted/50",
        className,
      )}
      {...props}
    />
  );
}
