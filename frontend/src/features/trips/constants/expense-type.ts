import type { ComboboxOption } from "@/components/form";
import type { ExpenseType } from "@/features/trips/types/trip-expense";

export const EXPENSE_TYPE_VALUES = [
  "diesel",
  "ice",
  "food",
  "labour",
  "harbour",
  "maintenance",
  "repair",
  "permit",
  "other",
] as const satisfies readonly ExpenseType[];

export const EXPENSE_TYPE_LABELS: Record<ExpenseType, string> = {
  diesel: "Diesel",
  ice: "Ice",
  food: "Food",
  labour: "Labour",
  harbour: "Harbour",
  maintenance: "Maintenance",
  repair: "Repair",
  permit: "Permit",
  other: "Other",
};

/** Expense Type as a select-options list, for the Trip Expense form's Expense Type field. */
export const EXPENSE_TYPE_OPTIONS: ComboboxOption<ExpenseType>[] = EXPENSE_TYPE_VALUES.map((value) => ({
  value,
  label: EXPENSE_TYPE_LABELS[value],
}));
