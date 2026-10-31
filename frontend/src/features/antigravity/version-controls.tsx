import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDateTimeInline } from "@/utils/formatters";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { getVersion, updateVersion, type VersionUpdate } from "./api";

export function AntigravityVersionControls({ readOnly }: { readOnly: boolean }) {
  const client = useQueryClient();
  const dateFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const query = useQuery({ queryKey: ["antigravity-version"], queryFn: getVersion, refetchInterval: 60000 });
  const save = useMutation({
    mutationFn: (body: VersionUpdate) => updateVersion(body),
    onSuccess: (status) => client.setQueryData(["antigravity-version"], status),
  });
  const status = query.data;
  const busy = readOnly || save.isPending || !status;
  return (
    <section className="space-y-2">
      <h3 className="text-[13px] font-medium">Antigravity CLI identity · all Antigravity accounts</h3>
      <p className="text-xs text-muted-foreground">
        Checks the CLI update manifest at startup and every 24 hours. A build is advertised only after its
        archive verified and its version and build changelist were read from it. Pin a verified build to hold
        or roll back the advertised identity.
      </p>
      {status && (
        <p className="text-xs">
          Effective:{" "}
          {status.effective ? status.effective.version + " (cl " + status.effective.changelist + ")" : "No verified build"}{" "}
          · {status.pinnedSha512 ? "Pinned" : "Following latest"}
          <br />
          Last checked: {status.lastCheckedAt ? formatDateTimeInline(status.lastCheckedAt, dateFormat) : "Never"}
          {status.retryAt ? " · retry " + formatDateTimeInline(status.retryAt, dateFormat) : ""}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Select
          value={status?.platform}
          disabled={busy}
          onValueChange={(platform) => save.mutate({ platform })}
        >
          <SelectTrigger aria-label="Antigravity CLI platform" className="h-8 w-full min-w-0 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {status?.platforms.map((platform) => (
              <SelectItem key={platform} value={platform}>
                {platform}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={status?.pinnedSha512 ?? undefined}
          disabled={busy || status.builds.length === 0}
          onValueChange={(pinnedSha512) => save.mutate({ pinnedSha512 })}
        >
          <SelectTrigger aria-label="Pinned Antigravity CLI build" className="h-8 w-full min-w-0 text-xs">
            <SelectValue placeholder="Pin a verified build" />
          </SelectTrigger>
          <SelectContent>
            {status?.builds.map((build) => (
              <SelectItem key={build.sha512} value={build.sha512}>
                {build.version} · cl {build.changelist}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          disabled={busy || !status.pinnedSha512}
          onClick={() => save.mutate({ clearPin: true })}
        >
          Follow latest
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Changing the platform clears the pin and the current build until that platform has been checked.
      </p>
      {[query.error?.message, save.error?.message, status?.error]
        .filter(Boolean)
        .map((message, index) => (
          <p key={index} role="alert" className="text-sm text-destructive">
            {message}
          </p>
        ))}
    </section>
  );
}
