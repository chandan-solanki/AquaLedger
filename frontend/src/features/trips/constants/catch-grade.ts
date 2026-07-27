import type { ComboboxOption } from "@/components/form";
import type { CatchGrade } from "@/features/trips/types/trip-catch";

export const CATCH_GRADE_VALUES = ["A", "B", "C"] as const satisfies readonly CatchGrade[];

export const CATCH_GRADE_LABELS: Record<CatchGrade, string> = {
  A: "Grade A",
  B: "Grade B",
  C: "Grade C",
};

/** Catch Grade as a select-options list, for the Trip Catch form's Grade field. */
export const CATCH_GRADE_OPTIONS: ComboboxOption<CatchGrade>[] = CATCH_GRADE_VALUES.map((value) => ({
  value,
  label: CATCH_GRADE_LABELS[value],
}));
