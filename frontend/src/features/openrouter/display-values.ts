import type { OpenRouterAccount } from "./api";

export const openRouterStatus = (account: OpenRouterAccount) =>
  account.isEnabled ? "active" : "paused";
export const openRouterBalance = (account: OpenRouterAccount) =>
  account.state.credits
    ? account.state.credits.total_credits - account.state.credits.total_usage
    : null;
/** Dollar amounts in the dashboard's en-US currency format, keeping OpenRouter's sub-cent balance precision. */
const moneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});
export const money = (value: number | null | undefined) =>
  value == null ? "Unknown" : moneyFormatter.format(value);
export const keyAllowance = (account: OpenRouterAccount) =>
  account.state.key?.limit === null
    ? "No key cap"
    : money(account.state.key?.limit_remaining);
