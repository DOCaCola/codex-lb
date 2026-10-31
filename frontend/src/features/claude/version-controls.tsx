import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { get, patch } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const schema = z.object({
  effectiveVersion: z.string(),
  discoveredVersion: z.string(),
  pinnedVersion: z.string().nullable(),
  lastCheckedAt: z.string().nullable(),
  lastChangedAt: z.string().nullable(),
  error: z.string().nullable(),
});
const path = "/api/claude-accounts/version";
export function ClaudeVersionControls({ readOnly }: { readOnly: boolean }) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["claude-version"],
    queryFn: () => get(path, schema),
    refetchInterval: 60000,
  });
  const [version, setVersion] = useState("");
  const pin = useMutation({
    mutationFn: (value: string | null) =>
      patch(path, schema, { body: { version: value } }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["claude-version"] }),
  });
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Checks stable releases at startup and every 24 hours. Pin an exact
        version to hold or roll back the advertised version. This does not
        install Claude Code or qualify a new compatibility profile.
      </p>
      {query.data && (
        <p className="text-xs">
          Effective: {query.data.effectiveVersion} ·{" "}
          {query.data.pinnedVersion ? "Pinned" : "Following stable"}
          <br />
          Last checked:{" "}
          {query.data.lastCheckedAt
            ? new Date(query.data.lastCheckedAt).toLocaleString()
            : "Never"}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Input
          aria-label="Pinned Claude Code version"
          placeholder="major.minor.patch"
          className="h-8 min-w-0 flex-1 basis-32 text-xs"
          value={version}
          disabled={readOnly || pin.isPending}
          onChange={(event) => setVersion(event.target.value)}
        />
        <Button
          size="sm"
          disabled={
            readOnly ||
            pin.isPending ||
            !/^\d{1,5}\.\d{1,5}\.\d{1,5}$/.test(version)
          }
          onClick={() => pin.mutate(version)}
        >
          Pin
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={readOnly || pin.isPending || !query.data?.pinnedVersion}
          onClick={() => pin.mutate(null)}
        >
          Follow stable
        </Button>
      </div>
      {[query.error?.message, pin.error?.message, query.data?.error]
        .filter(Boolean)
        .map((message, index) => (
          <p key={index} role="alert" className="text-sm text-destructive">
            {message}
          </p>
        ))}
    </div>
  );
}
