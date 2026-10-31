export const RANGE_PRESETS = ["7d", "30d", "90d"] as const;
export type RangePreset = (typeof RANGE_PRESETS)[number] | "custom";

export const PRESET_DAYS: Record<(typeof RANGE_PRESETS)[number], number> = { "7d": 7, "30d": 30, "90d": 90 };
