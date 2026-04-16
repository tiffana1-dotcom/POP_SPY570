/**
 * Planning-oriented retail calendar (holidays + seasonality).
 * Dates use the device local timezone. Lunar holidays use published Gregorian dates per year.
 */

export interface RetailMoment {
  id: string;
  label: string;
  /** When demand / merchandising typically peaks */
  peakDate: Date;
  /** How far ahead buyers often place POs (rough guide) */
  leadWeeks: number;
  /** Short planning note */
  buyerNotes: string;
  /** Suggested search / assortment keywords */
  focusKeywords: string[];
  /** Days from today until peak (negative = already passed this cycle) */
  daysUntilPeak: number;
  /** Within the next ~8 weeks */
  isWithin60d: boolean;
}

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function daysBetween(a: Date, b: Date): number {
  const ms = startOfDay(b).getTime() - startOfDay(a).getTime();
  return Math.round(ms / 86400000);
}

function nextAnnualDate(
  ref: Date,
  getForYear: (year: number) => Date,
): Date {
  const y = ref.getFullYear();
  let d = getForYear(y);
  if (startOfDay(d) < startOfDay(ref)) d = getForYear(y + 1);
  return d;
}

/** US Mother's Day — second Sunday in May */
function mothersDayUS(year: number): Date {
  const first = new Date(year, 4, 1);
  const firstDow = first.getDay();
  const toFirstSun = (7 - firstDow) % 7;
  const secondSun = 1 + toFirstSun + 7;
  return new Date(year, 4, secondSun);
}

/** US Father's Day — third Sunday in June */
function fathersDayUS(year: number): Date {
  const first = new Date(year, 5, 1);
  const firstDow = first.getDay();
  const toFirstSun = (7 - firstDow) % 7;
  const thirdSun = 1 + toFirstSun + 14;
  return new Date(year, 5, thirdSun);
}

/** Gregorian dates for Duanwu / Dragon Boat (lunar 5/5); moves yearly */
const DRAGON_BOAT: Partial<Record<number, { month: number; day: number }>> = {
  2025: { month: 4, day: 31 },
  2026: { month: 5, day: 19 },
  2027: { month: 5, day: 9 },
  2028: { month: 4, day: 28 },
  2029: { month: 5, day: 16 },
  2030: { month: 5, day: 5 },
};

/** Mid-Autumn — mooncake / gift season anchor (lunar 8/15) */
const MID_AUTUMN: Partial<Record<number, { month: number; day: number }>> = {
  2025: { month: 9, day: 6 },
  2026: { month: 8, day: 25 },
  2027: { month: 8, day: 15 },
  2028: { month: 8, day: 3 },
  2029: { month: 8, day: 22 },
  2030: { month: 8, day: 12 },
};

function dragonBoatPeak(year: number): Date {
  const g = DRAGON_BOAT[year];
  if (g) return new Date(year, g.month, g.day);
  return new Date(year, 5, 18);
}

function midAutumnPeak(year: number): Date {
  const g = MID_AUTUMN[year];
  if (g) return new Date(year, g.month, g.day);
  return new Date(year, 8, 25);
}

const EVENT_DEFS: {
  id: string;
  label: string;
  leadWeeks: number;
  buyerNotes: string;
  focusKeywords: string[];
  peak: (ref: Date) => Date;
}[] = [
  {
    id: "mothers-day-us",
    label: "Mother's Day (US)",
    leadWeeks: 6,
    buyerNotes:
      "Gift sets, tea, sweets, and premium snacks lift early; coordinate inbound air vs ocean.",
    focusKeywords: ["gift set", "tea assortment", "chocolate", "premium snack"],
    peak: (ref) => nextAnnualDate(ref, mothersDayUS),
  },
  {
    id: "fathers-day-us",
    label: "Father's Day (US)",
    leadWeeks: 5,
    buyerNotes:
      "Grilling, jerky, craft beverage adjacents, and portable snacks — watch club-store packs.",
    focusKeywords: ["jerky", "nuts", "energy bar", "grilling snack"],
    peak: (ref) => nextAnnualDate(ref, fathersDayUS),
  },
  {
    id: "dragon-boat",
    label: "Dragon Boat Festival (Duanwu)",
    leadWeeks: 8,
    buyerNotes:
      "Zongzi season + summer beverage adjacents; strong in APAC and diaspora retail — lunar date shifts yearly.",
    focusKeywords: ["zongzi", "rice dumpling", "Asian snack", "green tea"],
    peak: (ref) => nextAnnualDate(ref, dragonBoatPeak),
  },
  {
    id: "mid-autumn",
    label: "Mid-Autumn Festival",
    leadWeeks: 10,
    buyerNotes:
      "Mooncakes and gift tins lead; premium tea and fruit pairings — long lead for imports.",
    focusKeywords: ["mooncake", "gift tin", "oolong", "custard mooncake"],
    peak: (ref) => nextAnnualDate(ref, midAutumnPeak),
  },
];

export interface SeasonalContext {
  label: string;
  /** Northern-hemisphere seasonal framing for F&B */
  narrative: string;
  typicalDemand: string[];
}

/** Rough northern-hemisphere seasonal demand cues for grocery / Asian CPG */
export function getSeasonalContext(ref: Date = new Date()): SeasonalContext {
  const m = ref.getMonth();
  if (m === 11 || m <= 1) {
    return {
      label: "Winter / Lunar New Year runway",
      narrative:
        "Holiday gifting, pantry stocking, and travel snacks. Lunar New Year prep overlaps late Q4–Q1 depending on year.",
      typicalDemand: ["gift boxes", "candy", "tea", "instant hot pot", "rice crackers"],
    };
  }
  if (m >= 2 && m <= 4) {
    return {
      label: "Spring",
      narrative:
        "Mother's Day pipeline, spring cleaning pantry resets, lighter beverages and floral/tea adjacencies.",
      typicalDemand: ["tea", "light snacks", "giftable formats", "matcha"],
    };
  }
  if (m >= 5 && m <= 7) {
    return {
      label: "Summer",
      narrative:
        "Heat-stable snacks, hydration, outdoor/grilling adjacents, and festival SKUs (Dragon Boat, July 4 adjacency).",
      typicalDemand: ["jerky", "chilled drinks", "single-serve", "barbecue snack"],
    };
  }
  if (m >= 8 && m <= 10) {
    return {
      label: "Fall",
      narrative:
        "Back-to-school lunchbox, tailgating, and Mid-Autumn / holiday preview — mooncake and premium gifting.",
      typicalDemand: ["mooncake", "nuts", "portable breakfast", "premium chocolate"],
    };
  }
  return {
    label: "Late fall / holiday ramp",
    narrative:
      "Year-end gifting, baking, and pantry fills; align imports with ocean transit times.",
    typicalDemand: ["hot cocoa", "baking mix", "party snack", "advent calendars"],
  };
}

/**
 * Upcoming retail moments within `horizonDays`, sorted by nearest peak.
 */
export function getUpcomingRetailMoments(
  ref: Date = new Date(),
  horizonDays = 60,
): RetailMoment[] {
  const out: RetailMoment[] = [];
  for (const def of EVENT_DEFS) {
    const peakDate = def.peak(ref);
    const d = daysBetween(ref, peakDate);
    const isWithin60d = d >= -7 && d <= horizonDays;
    out.push({
      id: def.id,
      label: def.label,
      peakDate,
      leadWeeks: def.leadWeeks,
      buyerNotes: def.buyerNotes,
      focusKeywords: def.focusKeywords,
      daysUntilPeak: d,
      isWithin60d,
    });
  }
  return out
    .filter((x) => x.daysUntilPeak >= -14 && x.daysUntilPeak <= horizonDays)
    .sort((a, b) => a.daysUntilPeak - b.daysUntilPeak);
}
