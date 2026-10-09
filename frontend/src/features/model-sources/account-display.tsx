import { ProviderAccountName } from "@/components/brand/provider-account-name";
import { AccountSelectionSurface } from "@/components/account-surfaces";
import { StatusBadge } from "@/components/status-badge";
import { usePrivacyStore } from "@/hooks/use-privacy";
import {
  OPENAI_COMPATIBLE_LABEL,
  modelCountLabel,
  modelSourceStatus,
  sourceProtocols,
} from "./display-values";
import type { ModelSource } from "./schemas";

export function ModelSourceName({ source, color }: { source: ModelSource; color?: string }) {
  const blurred = usePrivacyStore((s) => s.blurred);
  return (
    <ProviderAccountName provider="openai_compatible" color={color}>
      <span className={blurred ? "privacy-blur" : undefined}>{source.name}</span>
    </ProviderAccountName>
  );
}

export function ModelSourceListItem({
  source,
  color,
  selected,
  onSelect,
}: {
  source: ModelSource;
  color?: string;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  // Same row anatomy as the other providers: title/subtitle and status, then a
  // one-line muted footer. The source reports no quota, so there is no meter.
  return (
    <AccountSelectionSurface selected={selected} onClick={() => onSelect(source.id)}>
      <div className="flex items-start gap-2.5">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">
            <ModelSourceName source={source} color={color} />
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {OPENAI_COMPATIBLE_LABEL} | {modelCountLabel(source)}
          </p>
        </div>
        <StatusBadge status={modelSourceStatus(source)} />
      </div>
      <div className="mt-2 flex min-w-0 items-center justify-between gap-2 text-[10px] text-muted-foreground">
        <span className="min-w-0 truncate">{source.baseUrl}</span>
        <span className="shrink-0">{sourceProtocols(source).join(" · ")}</span>
      </div>
    </AccountSelectionSurface>
  );
}
