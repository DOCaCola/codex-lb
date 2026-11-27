/** What a grant resets, from the windows it clears (agent-lb ResetCreditsView.kind). */
export function grantKind(clears: string[]): string {
  if (clears.includes("seven_day")) return "Full reset";
  if (clears.includes("seven_day_overage_included")) return "Fable reset";
  if (clears.includes("five_hour")) return "5-hour reset";
  return "Reset";
}
