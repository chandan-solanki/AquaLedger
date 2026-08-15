import type { StatusFilterOption } from "@/components/filters";

/** Mirrors the backend's RiskLevel enum (app/modules/reports/constants.py) - shared by the Outstanding and Aging Reports. */
export type RiskLevel = "low" | "medium" | "high";

export const RISK_LEVEL_VALUES = ["low", "medium", "high"] as const satisfies readonly RiskLevel[];

export const RISK_LEVEL_OPTIONS: StatusFilterOption<RiskLevel>[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};
