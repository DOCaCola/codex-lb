import { useEffect, useId, useState, type KeyboardEvent } from "react";
import { Check, ChevronsUpDown, Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

export type ModelPickerOption = {
  value: string;
  label: string;
  /** Second line; the value when omitted. */
  detail?: string;
  /** Short muted suffix after the label, such as "hidden". */
  note?: string;
  badge?: string;
  /** Shown faded but still selectable. */
  dimmed?: boolean;
  disabled?: boolean;
};

export type ModelPickerGroup = {
  id: string;
  label: string;
  caption?: string;
  /** A tinted section, separated from the sections after it. */
  highlighted?: boolean;
  options: ModelPickerOption[];
};

export type ModelPickerToggle = {
  label: string;
  checked: boolean;
  count: number;
  onCheckedChange: (checked: boolean) => void;
};

export type ModelPickerProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  groups: ModelPickerGroup[];
  placeholder: string;
  searchPlaceholder: string;
  /** Shown when no group offers any option. */
  emptyText: string;
  /** Offers the search text itself when it names no listed model. */
  allowCustom?: boolean;
  toggle?: ModelPickerToggle;
  disabled?: boolean;
  invalid?: boolean;
  describedBy?: string;
  autoFocus?: boolean;
  className?: string;
};

/** A searchable, sectioned model chooser. */
export function ModelPicker({
  label,
  value,
  onChange,
  groups,
  placeholder,
  searchPlaceholder,
  emptyText,
  allowCustom = false,
  toggle,
  disabled = false,
  invalid = false,
  describedBy,
  autoFocus,
  className,
}: ModelPickerProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const id = useId();
  const listId = `${id}-list`;
  const toggleId = `${id}-toggle`;
  const optionId = (index: number) => `${id}-option-${index}`;

  const search = query.trim();
  const needle = search.toLowerCase();
  const visible = groups
    .map((group) => ({
      ...group,
      options: group.options.filter(
        (option) => !needle || option.value.toLowerCase().includes(needle) || option.label.toLowerCase().includes(needle),
      ),
    }))
    .filter((group) => group.options.length > 0);
  const listed = groups.flatMap((group) => group.options);
  const custom = allowCustom && search && !listed.some((option) => option.value === search) ? search : null;
  const choices = [
    ...(custom ? [custom] : []),
    ...visible.flatMap((group) => group.options.filter((option) => !option.disabled).map((option) => option.value)),
  ];
  const activeIndex = Math.min(active, choices.length - 1);
  const selected = listed.find((option) => option.value === value);

  useEffect(() => {
    if (open && activeIndex >= 0) document.getElementById(`${id}-option-${activeIndex}`)?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex, id]);

  function changeOpen(next: boolean) {
    setOpen(next);
    setQuery("");
    setActive(0);
  }

  function choose(next: string) {
    onChange(next);
    changeOpen(false);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (choices.length === 0) return;
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((activeIndex + step + choices.length) % choices.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (activeIndex >= 0) choose(choices[activeIndex]);
    }
  }

  let index = custom ? 1 : 0;
  return (
    <Popover open={open} onOpenChange={changeOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          role="combobox"
          aria-label={label}
          aria-expanded={open}
          aria-controls={listId}
          aria-haspopup="listbox"
          aria-invalid={invalid}
          aria-describedby={describedBy}
          disabled={disabled}
          autoFocus={autoFocus}
          className={cn(
            "flex h-8 w-full min-w-[160px] items-center gap-1.5 rounded-md border border-input bg-background px-2 text-left text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-55",
            invalid && "border-destructive",
            className,
          )}
        >
          <span
            className={cn(
              "min-w-0 flex-1 truncate",
              !value && "text-muted-foreground",
              value && !selected && "font-mono",
            )}
          >
            {value ? (selected?.label ?? value) : placeholder}
          </span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[max(var(--radix-popover-trigger-width),22rem)] overflow-hidden p-0">
        <div className="flex items-center gap-1.5 border-b px-2.5">
          <Search className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            aria-label={searchPlaceholder}
            aria-controls={listId}
            aria-activedescendant={activeIndex >= 0 ? optionId(activeIndex) : undefined}
            placeholder={searchPlaceholder}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
            className="h-9 min-w-0 flex-1 bg-transparent text-xs outline-none [&::-webkit-search-cancel-button]:hidden"
          />
        </div>
        {toggle ? (
          <div className="flex items-center gap-2 border-b px-2.5 py-1.5 text-[11px] text-muted-foreground">
            <Switch
              id={toggleId}
              size="sm"
              checked={toggle.checked}
              onCheckedChange={(checked) => {
                toggle.onCheckedChange(checked);
                setActive(0);
              }}
            />
            <label htmlFor={toggleId} className="cursor-pointer select-none">{toggle.label}</label>
            <span className="ml-auto tabular-nums">{toggle.count}</span>
          </div>
        ) : null}
        <div id={listId} role="listbox" aria-label={label} className="max-h-72 overflow-y-auto p-1">
          {custom ? (
            <>
              <PickerOption
                id={optionId(0)}
                option={{ value: custom, label: t("modelPicker.useCustom", { value: custom }), detail: t("modelPicker.notInCatalogue") }}
                active={activeIndex === 0}
                selected={false}
                mono
                onHover={() => setActive(0)}
                onChoose={() => choose(custom)}
              />
              {visible.length > 0 ? <div className="mx-1 my-1 h-px bg-border" /> : null}
            </>
          ) : null}
          {visible.map((group, groupIndex) => (
            <div key={group.id}>
              <div
                role="group"
                aria-label={group.label}
                className={cn(group.highlighted && "rounded-md bg-violet-500/10 pb-0.5")}
              >
                <div
                  aria-hidden="true"
                  className={cn(
                    "px-2 pt-1.5 pb-0.5 text-[10.5px] font-semibold tracking-wide text-muted-foreground uppercase",
                    group.highlighted && "text-violet-700 dark:text-violet-300",
                  )}
                >
                  {group.label}
                  {group.caption ? <span className="font-normal tracking-normal normal-case"> · {group.caption}</span> : null}
                </div>
                {group.options.map((option) => {
                  const optionIndex = option.disabled ? -1 : index++;
                  return (
                    <PickerOption
                      key={option.value}
                      id={optionIndex >= 0 ? optionId(optionIndex) : undefined}
                      option={option}
                      active={optionIndex >= 0 && optionIndex === activeIndex}
                      selected={option.value === value}
                      onHover={() => {
                        if (optionIndex >= 0) setActive(optionIndex);
                      }}
                      onChoose={() => choose(option.value)}
                    />
                  );
                })}
              </div>
              {group.highlighted && groupIndex < visible.length - 1 ? <div className="mx-1 my-1.5 h-px bg-border" /> : null}
            </div>
          ))}
          {!custom && visible.length === 0 ? (
            <div className="px-3 py-4 text-center text-xs text-muted-foreground">
              {listed.length > 0 ? t("modelPicker.noMatches") : emptyText}
            </div>
          ) : null}
        </div>
        <div className="border-t px-2.5 py-1.5 text-[10.5px] text-muted-foreground">{t("modelPicker.keyboardHint")}</div>
      </PopoverContent>
    </Popover>
  );
}

function PickerOption({
  id,
  option,
  active,
  selected,
  mono = false,
  onHover,
  onChoose,
}: {
  id?: string;
  option: ModelPickerOption;
  active: boolean;
  selected: boolean;
  mono?: boolean;
  onHover: () => void;
  onChoose: () => void;
}) {
  return (
    <div
      id={id}
      role="option"
      aria-label={[option.label, option.note, option.badge].filter(Boolean).join(", ")}
      aria-selected={selected}
      aria-disabled={option.disabled || undefined}
      onMouseMove={onHover}
      onClick={option.disabled ? undefined : onChoose}
      className={cn(
        "flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-xs",
        active && "bg-accent",
        option.disabled && "cursor-not-allowed opacity-45",
      )}
    >
      <Check className={cn("size-3.5 shrink-0 text-primary", !selected && "invisible")} aria-hidden="true" />
      <span className={cn("flex min-w-0 flex-1 flex-col", option.dimmed && "opacity-60")}>
        <span className={cn("truncate font-medium", mono && "font-mono")}>
          {option.label}
          {option.note ? <span className="font-normal text-muted-foreground"> · {option.note}</span> : null}
        </span>
        <span className="truncate font-mono text-[10.5px] text-muted-foreground">{option.detail ?? option.value}</span>
      </span>
      {option.badge ? (
        <Badge variant="outline" className="shrink-0 px-1.5 py-0 text-[10px] font-normal text-muted-foreground">
          {option.badge}
        </Badge>
      ) : null}
    </div>
  );
}

