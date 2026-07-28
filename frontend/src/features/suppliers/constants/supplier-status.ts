import type { StatusFilterOption } from "@/components/filters";
import type { SupplierStatus } from "@/features/suppliers/types/supplier";

export const SUPPLIER_STATUS_VALUES = ["active", "inactive"] as const satisfies readonly SupplierStatus[];

export const SUPPLIER_STATUS_OPTIONS: StatusFilterOption<SupplierStatus>[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export const SUPPLIER_STATUS_LABELS: Record<SupplierStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};

/** Badge variant per status, mirroring `COMPANY_STATUS_BADGE_VARIANT`'s pattern. */
export const SUPPLIER_STATUS_BADGE_VARIANT: Record<SupplierStatus, "default" | "secondary"> = {
  active: "default",
  inactive: "secondary",
};
