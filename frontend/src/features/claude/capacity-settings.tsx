import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ClaudeCapacitySettings({
  value,
  readOnly,
  onSave,
}: {
  value: number | null;
  readOnly: boolean;
  onSave: (value: number | null) => Promise<unknown>;
}) {
  const [text, setText] = useState(value?.toString() ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const limit = text === "" ? null : Number(text);
  const valid = limit === null || (Number.isSafeInteger(limit) && limit > 0);
  return (
    <section className="space-y-3">
      <label className="space-y-1 text-sm">
        Maximum concurrent requests
        <Input
          type="number"
          min={1}
          step={1}
          placeholder="Unlimited"
          value={text}
          disabled={readOnly || busy}
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      <p className="text-xs text-muted-foreground">
        Per worker, across this account’s models. Leave empty for unlimited.
        Portable requests can use another available account; account-bound
        requests stay with their owner. This is not a provider quota.
      </p>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <Button
        variant="outline"
        disabled={readOnly || busy || !valid || limit === value}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await onSave(limit);
          } catch (cause) {
            setError(cause instanceof Error ? cause.message : "Could not save concurrency limit");
          } finally {
            setBusy(false);
          }
        }}
      >
        Save concurrency limit
      </Button>
    </section>
  );
}
