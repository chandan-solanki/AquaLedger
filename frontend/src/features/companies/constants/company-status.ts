import type { StatusFilterOption } from "@/components/filters";
import type { CompanyStatus } from "@/features/companies/types/company";

export const COMPANY_STATUS_VALUES = ["active", "inactive"] as const satisfies readonly CompanyStatus[];

export const COMPANY_STATUS_OPTIONS: StatusFilterOption<CompanyStatus>[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export const COMPANY_STATUS_LABELS: Record<CompanyStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};

/** Badge variant per status, per `02_DESIGN_SYSTEM.md`'s Status Badge category default. */
export const COMPANY_STATUS_BADGE_VARIANT: Record<CompanyStatus, "default" | "secondary"> = {
  active: "default",
  inactive: "secondary",
};
