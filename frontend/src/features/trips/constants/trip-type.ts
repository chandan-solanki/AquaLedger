import type { ComboboxOption } from "@/components/form";
import type { TripType } from "@/features/trips/types/trip";

export const TRIP_TYPE_VALUES = [
  "fishing",
  "transport",
  "maintenance",
  "other",
] as const satisfies readonly TripType[];

export const TRIP_TYPE_LABELS: Record<TripType, string> = {
  fishing: "Fishing",
  transport: "Transport",
  maintenance: "Maintenance",
  other: "Other",
};

/** Trip Type as a select-options list, for the Trip form's Trip Type field. */
export const TRIP_TYPE_OPTIONS: ComboboxOption<TripType>[] = TRIP_TYPE_VALUES.map((value) => ({
  value,
  label: TRIP_TYPE_LABELS[value],
}));
