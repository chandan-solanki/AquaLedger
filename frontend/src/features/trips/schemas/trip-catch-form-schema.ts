import { z } from "zod";

import { CATCH_GRADE_VALUES } from "@/features/trips/constants/catch-grade";
import type {
  TripCatch,
  TripCatchCreateRequest,
  TripCatchUpdateRequest,
} from "@/features/trips/types/trip-catch";

// Mirrors the backend's exact checks (app/modules/trip_catches/schemas.py):
// quantity_caught/available_quantity/sold_quantity/waste_quantity are all
// Decimal, max_digits=12, decimal_places=3.
const QUANTITY_PATTERN = /^\d{1,9}(\.\d{1,3})?$/;

const requiredQuantityField = z
  .string()
  .trim()
  .min(1, "Required")
  .refine((value) => QUANTITY_PATTERN.test(value), "Enter a valid quantity (up to 3 decimal places)")
  .refine((value) => Number(value) > 0, "Must be greater than 0");

const optionalQuantityField = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || QUANTITY_PATTERN.test(value),
    "Enter a valid quantity (up to 3 decimal places)"
  );

/**
 * Field names are snake_case, matching TripCatchCreateRequest/
 * TripCatchUpdateRequest exactly, mirroring `tripFormSchema`. There is no
 * `trip_id` field here - the owning trip is always the current Trip Detail
 * page's trip, supplied by the page (`toTripCatchRequestPayload(tripId, ...)`),
 * never chosen by the user (Sprint 6 Session 6's Navigation rule: "Users
 * should never manually choose the trip").
 *
 * `available_quantity`/`sold_quantity`/`waste_quantity` live in form state
 * always, but `TripCatchForm` only renders them in edit mode - the backend
 * fixes them to `quantity_caught`/`0`/`0` at creation and silently ignores
 * those keys on create (TripCatchCreateRequest has no such fields at all -
 * see trip-catch.ts), so `toTripCatchRequestPayload` never sends them
 * regardless of what's in `values`. The sum-invariant refinement below only
 * fires once all three carry a value (i.e. edit mode, where they're always
 * populated from the fetched record) - it mirrors the backend's own
 * `available + sold + waste == quantity_caught` check
 * (TripCatchService._ensure_quantity_invariant) for instant feedback; the
 * server re-validates with real Decimal precision and remains authoritative.
 */
export const tripCatchFormSchema = z
  .object({
    fish_id: z.string().trim().min(1, "Fish is required"),
    grade: z.union([z.enum(CATCH_GRADE_VALUES), z.literal("")]),
    quantity_caught: requiredQuantityField,
    available_quantity: optionalQuantityField,
    sold_quantity: optionalQuantityField,
    waste_quantity: optionalQuantityField,
    landing_date: z.string().trim().min(1, "Landing date is required"),
    landing_port: z.string().trim().max(100, "Must be 100 characters or fewer"),
    remarks: z.string().trim(),
  })
  .refine(
    (values) => {
      const { available_quantity, sold_quantity, waste_quantity, quantity_caught } = values;
      if (!available_quantity || !sold_quantity || !waste_quantity) return true;
      const sum = Number(available_quantity) + Number(sold_quantity) + Number(waste_quantity);
      return Math.abs(sum - Number(quantity_caught)) < 0.0005;
    },
    { message: "Available + Sold + Waste must equal Quantity Caught", path: ["available_quantity"] }
  );

export type TripCatchFormValues = z.infer<typeof tripCatchFormSchema>;

export const DEFAULT_TRIP_CATCH_FORM_VALUES: TripCatchFormValues = {
  fish_id: "",
  grade: "",
  quantity_caught: "",
  available_quantity: "",
  sold_quantity: "",
  waste_quantity: "",
  landing_date: "",
  landing_port: "",
  remarks: "",
};

/** Populates the form from a fetched `TripCatch` for the Edit page - null fields become empty strings. */
export function toTripCatchFormValues(tripCatch: TripCatch): TripCatchFormValues {
  return {
    fish_id: tripCatch.fishId,
    grade: tripCatch.grade ?? "",
    quantity_caught: tripCatch.quantityCaught,
    available_quantity: tripCatch.availableQuantity,
    sold_quantity: tripCatch.soldQuantity,
    waste_quantity: tripCatch.wasteQuantity,
    landing_date: tripCatch.landingDate,
    landing_port: tripCatch.landingPort ?? "",
    remarks: tripCatch.remarks ?? "",
  };
}

/**
 * Maps form values onto the Create payload - `tripId` comes from the Trip
 * Detail page's route, never the form. `available_quantity`/`sold_quantity`/
 * `waste_quantity` are never included, matching `TripCatchCreateRequest`'s
 * actual field set.
 */
export function toTripCatchRequestPayload(tripId: string, values: TripCatchFormValues): TripCatchCreateRequest {
  return {
    trip_id: tripId,
    fish_id: values.fish_id,
    grade: values.grade || undefined,
    quantity_caught: values.quantity_caught,
    landing_date: values.landing_date,
    landing_port: values.landing_port || undefined,
    remarks: values.remarks || undefined,
  };
}

/**
 * Maps form values onto the Update payload - unlike create, this includes
 * `available_quantity`/`sold_quantity`/`waste_quantity`, matching
 * `TripCatchUpdateRequest`'s actual field set. No `trip_id` - this form has
 * no trip selector in either mode, so reassignment is never offered.
 */
export function toTripCatchUpdatePayload(values: TripCatchFormValues): TripCatchUpdateRequest {
  return {
    fish_id: values.fish_id,
    grade: values.grade || undefined,
    quantity_caught: values.quantity_caught,
    available_quantity: values.available_quantity || undefined,
    sold_quantity: values.sold_quantity || undefined,
    waste_quantity: values.waste_quantity || undefined,
    landing_date: values.landing_date,
    landing_port: values.landing_port || undefined,
    remarks: values.remarks || undefined,
  };
}
