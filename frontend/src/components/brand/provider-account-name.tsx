import type { ReactNode } from "react";

export type AccountProvider = "codex" | "claude" | "openrouter";

export function ProviderLogo({ provider }: { provider: AccountProvider }) {
  return (
    <img
      src={`/images/providers/${provider === "codex" ? "openai" : provider}.svg`}
      alt=""
      aria-hidden="true"
      width={16}
      height={16}
      className="size-4 shrink-0 object-contain dark:invert"
      data-provider={provider}
    />
  );
}

export function ProviderAccountName({ provider, children }: {
  provider: AccountProvider | null;
  children: ReactNode;
}) {
  return (
    <span className="inline-flex min-w-0 max-w-full items-center gap-1.5 align-middle">
      {provider ? <ProviderLogo provider={provider} /> : null}
      <span className="min-w-0 truncate">{children}</span>
    </span>
  );
}
