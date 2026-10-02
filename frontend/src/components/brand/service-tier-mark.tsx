const ICONS: Record<string, string> = {
  priority: "fast",
  ultrafast: "ultrafast",
};

/** Billable tier marker: the Codex Fast/Ultrafast glyph drawn in the current
 * text color through a CSS mask, or the tier name for tiers without one. */
export function ServiceTierMark({
  tier,
  label,
}: {
  tier: string;
  label: string;
}) {
  const icon = ICONS[tier];
  if (!icon) {
    return <span className="text-muted-foreground">{label}</span>;
  }
  const mask = `url(/images/service-tiers/${icon}.svg) center / contain no-repeat`;
  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      data-service-tier={tier}
      className="inline-block size-3.5 shrink-0 bg-current align-[-2px] text-muted-foreground"
      style={{ mask, WebkitMask: mask }}
    />
  );
}
