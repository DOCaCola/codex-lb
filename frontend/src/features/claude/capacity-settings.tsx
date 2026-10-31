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
    <section className="space-y-1.5">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <label htmlFor="max-concurrent-requests" className="text-[13px] font-medium">
          Maximum concurrent requests
        </label>
        <div className="flex shrink-0 items-center gap-1.5">
          <Input
            id="max-concurrent-requests"
            type="number"
            min={1}
            step={1}
            placeholder="Unlimited"
            className="h-8 w-28 text-right text-xs tabular-nums"
            value={text}
            disabled={readOnly || busy}
            onChange={(event) => setText(event.target.value)}
          />
          <Button
            variant="outline"
            size="sm"
            aria-label="Save concurrency limit"
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
            Save
          </Button>
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground">
        Per worker, across this account’s models. Leave empty for unlimited.
        Portable requests can use another available account; account-bound
        requests stay with their owner. This is not a provider quota.
      </p>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </section>
  );
}
