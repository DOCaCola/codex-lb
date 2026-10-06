import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ChartToggleProps<T extends string> = {
  label: string;
  value: T;
  options: { value: T; label: string; icon?: ReactNode }[];
  onChange: (value: T) => void;
};

export function ChartToggle<T extends string>({ label, value, options, onChange }: ChartToggleProps<T>) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded-md border bg-muted/30 p-0.5">
      {options.map((option) => {
        const isActive = option.value === value;
        return (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant="ghost"
            aria-pressed={isActive}
            className={cn(
              "h-6 gap-1.5 rounded-[5px] px-2 text-[11px] font-semibold uppercase tracking-wide",
              isActive
                ? "bg-background text-foreground shadow-sm hover:bg-background"
                : "text-muted-foreground hover:bg-transparent hover:text-foreground",
            )}
            onClick={() => onChange(option.value)}
          >
            {option.icon}
            {option.label}
          </Button>
        );
      })}
    </div>
  );
}
