import type { StatusFilterOption } from "@/components/filters";

/** Mirrors the backend's PaidStatus enum (app/modules/reports/constants.py) - shared by the Sales and Purchase Reports, since the concept is identical on both sides. */
export type PaidStatus = "unpaid" | "partially_paid" | "paid";

export const PAID_STATUS_VALUES = ["unpaid", "partially_paid", "paid"] as const satisfies readonly PaidStatus[];

export const PAID_STATUS_OPTIONS: StatusFilterOption<PaidStatus>[] = [
  { value: "unpaid", label: "Unpaid" },
  { value: "partially_paid", label: "Partially Paid" },
  { value: "paid", label: "Paid" },
];

export const PAID_STATUS_LABELS: Record<PaidStatus, string> = {
  unpaid: "Unpaid",
  partially_paid: "Partially Paid",
  paid: "Paid",
};
