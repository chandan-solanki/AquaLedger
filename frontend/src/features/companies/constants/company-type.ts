import type { ComboboxOption } from "@/components/form";
import type { CompanyType } from "@/features/companies/types/company";

export const COMPANY_TYPE_OPTIONS: ComboboxOption<CompanyType>[] = [
  { value: "customer", label: "Customer" },
  { value: "supplier", label: "Supplier" },
  { value: "both", label: "Customer & Supplier" },
];

export const COMPANY_TYPE_LABELS: Record<CompanyType, string> = {
  customer: "Customer",
  supplier: "Supplier",
  both: "Customer & Supplier",
};
