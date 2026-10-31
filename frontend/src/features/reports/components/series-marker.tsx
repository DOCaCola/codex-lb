import { ProviderLogo } from "@/components/brand/provider-account-name";

import type { SeriesStyle } from "../report-series-styles";

/** Provider logo in the series colour, or a dot of the same footprint. */
export function SeriesMarker({ style }: { style: Pick<SeriesStyle, "color" | "provider"> }) {
  if (style.provider) {
    return <ProviderLogo provider={style.provider} color={style.color} />;
  }
  return (
    <span aria-hidden="true" className="flex size-4 shrink-0 items-center justify-center">
      <span className="size-2.5 rounded-full" style={{ backgroundColor: style.color }} />
    </span>
  );
}
