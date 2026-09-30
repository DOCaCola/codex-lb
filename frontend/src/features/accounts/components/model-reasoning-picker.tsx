import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export type ReasoningRestrictions = Record<string, string[]>;

export function ModelReasoningPicker({
  model,
  levels,
  value,
  disabled,
  onChange,
}: {
  model: string;
  levels: string[];
  value: string[] | undefined;
  disabled: boolean;
  onChange: (value: string[] | undefined) => void;
}) {
  const entries = [...new Set([...levels, ...(value ?? [])])];
  if (entries.length === 0) return null;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="h-auto max-w-full whitespace-normal text-left"
          disabled={disabled}
          aria-label={`Allowed reasoning for ${model}`}
        >
          Reasoning: {value ? value.join(", ") : "All supported"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuLabel>Allowed reasoning</DropdownMenuLabel>
        <DropdownMenuCheckboxItem
          checked={value === undefined}
          onSelect={(event) => event.preventDefault()}
          onCheckedChange={() => onChange(undefined)}
        >
          All supported
        </DropdownMenuCheckboxItem>
        <DropdownMenuSeparator />
        {entries.map((level) => {
          const selected = value ?? levels;
          return (
            <DropdownMenuCheckboxItem
              key={level}
              checked={selected.includes(level)}
              disabled={selected.length === 1 && selected.includes(level)}
              onSelect={(event) => event.preventDefault()}
              onCheckedChange={(checked) =>
                onChange(
                  checked
                    ? [...selected, level]
                    : selected.filter((item) => item !== level),
                )
              }
            >
              {level === "none" ? "None (no reasoning)" : level}
              {!levels.includes(level) ? " — Currently unavailable" : ""}
            </DropdownMenuCheckboxItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
