import { useId } from "react";
import { Switch } from "@/components/ui/switch";

export function AccountModelMode({
  allModels,
  disabled,
  onChange,
}: {
  allModels: boolean;
  disabled: boolean;
  onChange: (value: boolean) => void;
}) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className="flex min-w-0 items-center justify-between gap-3 rounded-md border px-3 py-2"
    >
      <span className="min-w-0">
        <span className="block text-xs font-medium">All models</span>
        <span className="block text-xs text-muted-foreground">
          {allModels
            ? "All available conversation models, including new models."
            : "Only selected conversation models are available to clients."}
        </span>
      </span>
      <Switch
        id={id}
        className="shrink-0"
        checked={allModels}
        disabled={disabled}
        onCheckedChange={onChange}
      />
    </label>
  );
}
