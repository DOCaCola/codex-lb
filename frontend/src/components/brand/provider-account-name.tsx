import type { ReactNode } from "react";

import type { AccountProvider } from "./account-provider";

export type { AccountProvider };

function providerLogoUrl(provider: AccountProvider): string {
  return `/images/providers/${provider === "codex" ? "openai" : provider}.svg`;
}

const LOGO_SIZES = { sm: "size-4", md: "size-5", lg: "size-7" } as const;

/** Brand logo; with `color`, the logo shape is painted in the account's chart colour. */
export function ProviderLogo({
  provider,
  color,
  size = "sm",
}: {
  provider: AccountProvider;
  color?: string;
  size?: keyof typeof LOGO_SIZES;
}) {
  if (color) {
    const mask = `url(${providerLogoUrl(provider)}) center / contain no-repeat`;
    return (
      <span
        aria-hidden="true"
        className={`inline-block shrink-0 ${LOGO_SIZES[size]}`}
        style={{ backgroundColor: color, mask, WebkitMask: mask }}
        data-provider={provider}
      />
    );
  }
  return (
    <img
      src={providerLogoUrl(provider)}
      alt=""
      aria-hidden="true"
      className={`shrink-0 object-contain dark:invert ${LOGO_SIZES[size]}`}
      data-provider={provider}
    />
  );
}

export function ProviderAccountName({ provider, color, children }: {
  provider: AccountProvider | null;
  color?: string;
  children: ReactNode;
}) {
  return (
    <span className="inline-flex min-w-0 max-w-full items-center gap-1.5 align-middle">
      {provider ? <ProviderLogo provider={provider} color={color} /> : null}
      <span className="min-w-0 truncate">{children}</span>
    </span>
  );
}
