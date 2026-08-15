import type { StatusFilterOption } from "@/components/filters";

/** Mirrors the backend's ProfitabilityFilter enum (app/modules/reports/constants.py) - the Trip/Boat Profitability reports' single "Profitability" filter (Profitable Only/Loss Only presented as one mutually-exclusive choice, not two independent toggles). */
export type ProfitabilityFilter = "profitable" | "loss";

export const PROFITABILITY_FILTER_VALUES = [
  "profitable",
  "loss",
] as const satisfies readonly ProfitabilityFilter[];

export const PROFITABILITY_FILTER_OPTIONS: StatusFilterOption<ProfitabilityFilter>[] = [
  { value: "profitable", label: "Profitable Only" },
  { value: "loss", label: "Loss Only" },
];
