/**
 * Shared number / currency formatting utilities.
 * Single source of truth -- import from here instead of creating local formatters.
 */

const ilsFormatter = new Intl.NumberFormat("he-IL", {
  style: "currency",
  currency: "ILS",
});

const numberFormatter = new Intl.NumberFormat("he-IL");

/** Format a number as Israeli Shekel currency string. */
export function formatILS(amount: number): string {
  return ilsFormatter.format(amount);
}

/** Format a plain number with Hebrew-IL grouping. */
export function formatNumber(n: number): string {
  return numberFormatter.format(n);
}

/** Format a square-meter area value, e.g. '120 מ"ר'. */
export function formatArea(sqm: number): string {
  return `${numberFormatter.format(sqm)} מ"ר`;
}
