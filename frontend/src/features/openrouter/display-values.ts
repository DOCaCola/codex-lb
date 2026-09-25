import type { OpenRouterAccount } from "./api";

export const openRouterStatus = (account: OpenRouterAccount) =>
  account.isEnabled ? "active" : "paused";
export const openRouterBalance = (account: OpenRouterAccount) =>
  account.state.credits
    ? account.state.credits.total_credits - account.state.credits.total_usage
    : null;
export const money = (value: number | null | undefined) =>
  value == null
    ? "Unknown"
    : new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 4,
      }).format(value);
export const keyAllowance = (account: OpenRouterAccount) =>
  account.state.key?.limit === null
    ? "No key cap"
    : money(account.state.key?.limit_remaining);
