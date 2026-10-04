import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  ACCOUNT_COLOR_KEYS,
  accountColorPalette,
  findAccountColor,
  useAccountColors,
  useSetAccountColor,
  type AccountColorTarget,
} from "@/features/accounts/account-colors";
import { useThemeStore } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";

function ColorDot({ color, className }: { color: string; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn("size-3.5 shrink-0 rounded-full shadow-[inset_0_0_0_1px_rgb(0_0_0/0.12)]", className)}
      style={{ backgroundColor: color }}
    />
  );
}

/** Chart colour button for an account detail heading; the swatches open in a popover. */
export function AccountColorPicker({ target, disabled }: { target: AccountColorTarget; disabled: boolean }) {
  const { t } = useTranslation();
  const isDark = useThemeStore((s) => s.theme === "dark");
  const { data: colors } = useAccountColors();
  const setColor = useSetAccountColor(target);
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);
  const entry = findAccountColor(colors, target);
  if (!colors || !entry) return null;

  const palette = accountColorPalette(isDark);
  const colorName = (index: number) => t(`accounts.color.names.${ACCOUNT_COLOR_KEYS[index]}`);
  const usedByOthers = new Set(colors.filter((other) => other !== entry).map((other) => other.color));
  const automaticLabel = t("accounts.color.automatic", { color: colorName(entry.automaticColor) });
  const restingLabel = entry.chartColor === null ? automaticLabel : colorName(entry.chartColor);
  const choose = (chartColor: number | null) => {
    setOpen(false);
    if (chartColor !== entry.chartColor) setColor.mutate(chartColor);
  };

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setHovered(null);
      }}
    >
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          aria-label={t("accounts.color.button")}
          title={t("accounts.color.button")}
          disabled={disabled || setColor.isPending}
        >
          <ColorDot color={palette[entry.color]} />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-max p-3" aria-label={t("accounts.color.button")}>
        <button
          type="button"
          className={cn(
            "flex h-[30px] w-full items-center gap-2 rounded-md border px-2 text-xs hover:bg-muted",
            entry.chartColor === null && "border-ring",
          )}
          aria-pressed={entry.chartColor === null}
          onClick={() => choose(null)}
        >
          <ColorDot color={palette[entry.automaticColor]} className="size-3" />
          {automaticLabel}
        </button>
        <div className="mt-2.5 grid grid-cols-[repeat(6,1.5rem)] gap-2">
          {ACCOUNT_COLOR_KEYS.map((key, index) => (
            <button
              key={key}
              type="button"
              className={cn(
                "relative size-6 rounded-full outline-2 outline-offset-2 outline-transparent",
                entry.chartColor === index && "outline-ring",
              )}
              style={{ backgroundColor: palette[index] }}
              aria-label={colorName(index)}
              aria-pressed={entry.chartColor === index}
              data-in-use={usedByOthers.has(index) ? "true" : undefined}
              onMouseEnter={() => setHovered(index)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(index)}
              onBlur={() => setHovered(null)}
              onClick={() => choose(index)}
            >
              {usedByOthers.has(index) ? (
                <span
                  aria-hidden="true"
                  className="absolute -right-0.5 -bottom-0.5 size-[9px] rounded-full border-2 border-muted-foreground bg-popover"
                />
              ) : null}
            </button>
          ))}
        </div>
        <p className="mt-2.5 min-h-4 text-xs text-muted-foreground">
          {hovered === null
            ? restingLabel
            : usedByOthers.has(hovered)
              ? t("accounts.color.inUse", { color: colorName(hovered) })
              : colorName(hovered)}
        </p>
      </PopoverContent>
    </Popover>
  );
}
