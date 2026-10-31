import type { DateDisplayFormat } from "@/hooks/use-date-format";
import { getIntlLocale } from "@/utils/formatters";

const REPORTS_TIMEZONE_STORAGE_KEY = "codex-lb-reports-timezone";

function isValidTimeZone(timeZone: string | undefined): timeZone is string {
  if (!timeZone) {
    return false;
  }

  if (typeof Intl.supportedValuesOf === "function") {
    return timeZone === "UTC" || Intl.supportedValuesOf("timeZone").includes(timeZone);
  }

  try {
    new Intl.DateTimeFormat(undefined, { timeZone });
    return true;
  } catch {
    return false;
  }
}

export function getBrowserReportsTimeZone(): string | undefined {
  const detectedTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (isValidTimeZone(detectedTimeZone)) {
    try {
      window.localStorage.setItem(REPORTS_TIMEZONE_STORAGE_KEY, detectedTimeZone);
    } catch {
      // Some browser contexts block storage access; detection still succeeded.
    }
    return detectedTimeZone;
  }

  try {
    const cachedTimeZone = window.localStorage.getItem(REPORTS_TIMEZONE_STORAGE_KEY) ?? undefined;
    if (isValidTimeZone(cachedTimeZone)) {
      return cachedTimeZone;
    }
  } catch {
    // Some browser contexts block storage access; fall through and omit timezone.
  }

  return undefined;
}

export function localDateISO(date: Date = new Date()): string {
  const localTime = date.getTime() - date.getTimezoneOffset() * 60_000;
  return new Date(localTime).toISOString().slice(0, 10);
}

export function daysAgoLocalISO(days: number, date: Date = new Date()): string {
  const shifted = new Date(date);
  shifted.setDate(shifted.getDate() - days);
  return localDateISO(shifted);
}

export function isReportDateRangeValid(
  startDate: string | undefined,
  endDate: string | undefined,
): boolean {
  return !startDate || !endDate || startDate <= endDate;
}

// Report days are calendar dates; formatting them at UTC midnight keeps the
// browser's offset from shifting them to a neighbouring day.
function reportDay(date: string): Date {
  return new Date(`${date}T00:00:00Z`);
}

const DAY_STYLES = {
  long: { weekday: "short", day: "numeric", month: "short" },
  short: { day: "numeric", month: "short" },
} as const satisfies Record<string, Intl.DateTimeFormatOptions>;

/** A report day: "Sun, Oct 25" (`long`) or "Oct 25" (`short`), or ISO when that preference is selected. */
export function formatReportDay(
  date: string,
  displayFormat: DateDisplayFormat,
  style: keyof typeof DAY_STYLES = "long",
): string {
  if (displayFormat === "iso8601") {
    return style === "long" ? date : date.slice(5);
  }
  return new Intl.DateTimeFormat(getIntlLocale(), { ...DAY_STYLES[style], timeZone: "UTC" }).format(reportDay(date));
}

/** A report window, e.g. "Sun, Oct 25 – Sat, Oct 31, 2026"; `withYear: false` for the comparison window. */
export function formatReportRange(
  startDate: string,
  endDate: string,
  displayFormat: DateDisplayFormat,
  { withYear = true }: { withYear?: boolean } = {},
): string {
  if (displayFormat === "iso8601") {
    return `${startDate} – ${endDate}`;
  }
  const formatter = new Intl.DateTimeFormat(getIntlLocale(), {
    ...(withYear ? { ...DAY_STYLES.long, year: "numeric" } : DAY_STYLES.short),
    timeZone: "UTC",
  });
  return formatter.formatRange(reportDay(startDate), reportDay(endDate));
}
