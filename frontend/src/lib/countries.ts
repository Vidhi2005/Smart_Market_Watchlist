// Curated country -> primary IANA timezone list. Not exhaustive — covers
// the markets this app actually tracks (US, India) plus enough common
// countries for a real signup flow. "Other" falls back to the browser's
// own detected timezone rather than guessing.

export interface CountryOption {
  code: string;
  label: string;
  timezone: string;
}

export const COUNTRIES: CountryOption[] = [
  { code: "IN", label: "India", timezone: "Asia/Kolkata" },
  { code: "US", label: "United States", timezone: "America/New_York" },
  { code: "GB", label: "United Kingdom", timezone: "Europe/London" },
  { code: "CA", label: "Canada", timezone: "America/Toronto" },
  { code: "AU", label: "Australia", timezone: "Australia/Sydney" },
  { code: "SG", label: "Singapore", timezone: "Asia/Singapore" },
  { code: "AE", label: "United Arab Emirates", timezone: "Asia/Dubai" },
  { code: "DE", label: "Germany", timezone: "Europe/Berlin" },
  { code: "FR", label: "France", timezone: "Europe/Paris" },
  { code: "JP", label: "Japan", timezone: "Asia/Tokyo" },
  { code: "CN", label: "China", timezone: "Asia/Shanghai" },
  { code: "HK", label: "Hong Kong", timezone: "Asia/Hong_Kong" },
  { code: "BR", label: "Brazil", timezone: "America/Sao_Paulo" },
  { code: "ZA", label: "South Africa", timezone: "Africa/Johannesburg" },
  { code: "NZ", label: "New Zealand", timezone: "Pacific/Auckland" },
];

/** Best-effort detection of the visitor's own timezone, for a sensible default. */
export function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

/** If the detected timezone matches a curated country, pre-select it. */
export function guessCountryCode(): string | null {
  const tz = detectTimezone();
  return COUNTRIES.find((c) => c.timezone === tz)?.code ?? null;
}
