import type { OpenAIApiAccount } from "./api";

export const OPENAI_API_LABEL = "OpenAI API";
/** Published model ids carry this prefix; the bare id is the subscription pool's model. */
export const OPENAI_API_MODEL_PREFIX = "openai-apikey/";

const moneyFormatter = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
export const money = (value: number | null | undefined) =>
  value == null ? "Unknown" : moneyFormatter.format(value);

/** An OpenAI billing refusal is authoritative over the recorded-spend estimate. */
export function creditExhausted(account: OpenAIApiAccount, now = Date.now()): boolean {
  const until = account.credit.exhaustedUntil;
  return until !== null && Date.parse(until) > now;
}

export function openAIApiStatus(account: OpenAIApiAccount, now = Date.now()) {
  if (!account.isEnabled) return "paused";
  return creditExhausted(account, now) ? "exceeded" : "active";
}

/** Estimated credit left as a share of the monthly credit; null without a configured amount. */
export function creditPercentLeft(account: OpenAIApiAccount): number | null {
  const { monthlyCreditUsd, remainingUsd } = account.credit;
  if (monthlyCreditUsd === null || remainingUsd === null || monthlyCreditUsd <= 0) return null;
  return Math.max(0, Math.min(100, (remainingUsd / monthlyCreditUsd) * 100));
}

export function selectionCounts(account: OpenAIApiAccount): { text: number; image: number } {
  const catalog = new Map(account.state.catalog.map((model) => [model.id, model]));
  const image = account.state.selections.filter((selection) => catalog.get(selection.model)?.kind === "image").length;
  return { text: account.state.selections.length - image, image };
}
