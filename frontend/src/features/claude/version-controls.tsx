import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { get, patch } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDateTimeInline } from "@/utils/formatters";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";

const build = z.object({
  version: z.string(),
  sdkVersion: z.string(),
  runtimeVersion: z.string(),
  verifiedAt: z.string().nullable(),
});
const schema = z.object({
  effective: build,
  discoveredVersion: z.string(),
  pinnedVersion: z.string().nullable(),
  builds: z.array(build),
  lastCheckedAt: z.string().nullable(),
  lastChangedAt: z.string().nullable(),
  retryAt: z.string().nullable(),
  error: z.string().nullable(),
});
const path = "/api/claude-accounts/version";

export function ClaudeVersionControls({ readOnly }: { readOnly: boolean }) {
  const client = useQueryClient();
  const dateFormat = useDateDisplayFormatStore(
    (state) => state.dateDisplayFormat,
  );
  const query = useQuery({
    queryKey: ["claude-version"],
    queryFn: () => get(path, schema),
    refetchInterval: 60000,
  });
  const pin = useMutation({
    mutationFn: (value: string | null) =>
      patch(path, schema, { body: { version: value } }),
    onSuccess: (status) => client.setQueryData(["claude-version"], status),
  });
  const status = query.data;
  const busy = readOnly || pin.isPending || !status;
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Checks stable releases at startup and every 24 hours. A release is
        advertised only after its published build was verified and its SDK and
        runtime versions were read from it. Pin a verified build to hold or roll
        back the advertised identity.
      </p>
      {status && (
        <p className="text-xs">
          Effective: {status.effective.version} (SDK{" "}
          {status.effective.sdkVersion}, runtime{" "}
          {status.effective.runtimeVersion}) ·{" "}
          {status.pinnedVersion ? "Pinned" : "Following stable"}
          <br />
          Last checked:{" "}
          {status.lastCheckedAt
            ? formatDateTimeInline(status.lastCheckedAt, dateFormat)
            : "Never"}
          {status.retryAt
            ? " · retry " + formatDateTimeInline(status.retryAt, dateFormat)
            : ""}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Select
          value={status?.pinnedVersion ?? undefined}
          disabled={busy}
          onValueChange={(value) => pin.mutate(value)}
        >
          <SelectTrigger
            aria-label="Pinned Claude Code version"
            className="h-8 min-w-0 flex-1 basis-32 text-xs"
          >
            <SelectValue placeholder="Pin a verified build" />
          </SelectTrigger>
          <SelectContent>
            {status?.builds.map((item) => (
              <SelectItem key={item.version} value={item.version}>
                {item.version} · SDK {item.sdkVersion} · {item.runtimeVersion}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          disabled={busy || !status.pinnedVersion}
          onClick={() => pin.mutate(null)}
        >
          Follow stable
        </Button>
      </div>
      {[query.error?.message, pin.error?.message, status?.error]
        .filter(Boolean)
        .map((message, index) => (
          <p key={index} role="alert" className="text-sm text-destructive">
            {message}
          </p>
        ))}
    </div>
  );
}
