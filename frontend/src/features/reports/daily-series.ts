import type { DailyReportRow } from "./schemas";

/** Every calendar day from startDate through endDate; empty for an invalid or inverted range. */
export function calendarDays(startDate: string, endDate: string): string[] {
  if (!isISODate(startDate) || !isISODate(endDate) || startDate > endDate) {
    return [];
  }
  const days: string[] = [];
  for (let current = startDate; current <= endDate; current = shiftISODate(current, 1)) {
    days.push(current);
  }
  return days;
}

export function shiftISODate(date: string, days: number): string {
  const shifted = new Date(`${date}T00:00:00Z`);
  shifted.setUTCDate(shifted.getUTCDate() + days);
  return shifted.toISOString().slice(0, 10);
}

export function buildContinuousDailyRows(
  startDate: string,
  endDate: string,
  rows: DailyReportRow[],
): DailyReportRow[] {
  const days = calendarDays(startDate, endDate);
  if (days.length === 0) {
    return rows;
  }
  const rowsByDate = new Map(rows.map((row) => [row.date, row]));
  return days.map((day) => rowsByDate.get(day) ?? createZeroRow(day));
}

function isISODate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }

  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function createZeroRow(date: string): DailyReportRow {
  return {
    date,
    requests: 0,
    conversations: 0,
    inputTokens: 0,
    outputTokens: 0,
    reasoningTokens: 0,
    cachedInputTokens: 0,
    costUsd: 0,
    activeAccounts: 0,
    cancelledCount: 0,
    errorCount: 0,
    medianTtftMs: 0,
    medianTps: 0,
    medianQueueMs: 0,
  };
}
