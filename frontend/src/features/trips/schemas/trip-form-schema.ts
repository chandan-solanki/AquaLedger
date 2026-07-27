import { format, parseISO } from "date-fns";
import { z } from "zod";

import { TRIP_STATUS_VALUES } from "@/features/trips/constants/trip-status";
import { TRIP_TYPE_VALUES } from "@/features/trips/constants/trip-type";
import type { Trip, TripCreateRequest, TripUpdateRequest } from "@/features/trips/types/trip";

// Native <input type="datetime-local">'s own value format (no timezone -
// browsers emit minute precision by default): "YYYY-MM-DDTHH:mm". Kept as a
// plain string in form state, matching how the rest of this form's raw
// `Input`-backed fields work - converted to/from an ISO instant only at the
// `toTripFormValues`/`toTripRequestPayload` boundary.
const DATETIME_LOCAL_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;

const requiredDatetimeField = z
  .string()
  .trim()
  .min(1, "Departure date and time is required")
  .refine((value) => DATETIME_LOCAL_PATTERN.test(value), "Enter a valid date and time");

const optionalDatetimeField = z
  .string()
  .trim()
  .refine((value) => value === "" || DATETIME_LOCAL_PATTERN.test(value), "Enter a valid date and time");

/**
 * Field names are snake_case, matching TripCreateRequest/TripUpdateRequest
 * exactly (not the client's camelCase `Trip` type) - so
 * `mapServerErrorsToForm` can set a 422's `field_errors` directly onto the
 * right RHF field with no translation layer, mirroring `boatFormSchema`.
 *
 * The `actual_return_datetime >= departure_datetime` check mirrors the
 * backend's own `TripService._ensure_return_after_departure` invariant
 * (app/modules/trips/service.py) - same rule, enforced earlier for instant
 * feedback; the server still re-validates and remains the source of truth.
 * datetime-local strings compare correctly as plain strings since the format
 * is fixed-width and zero-padded (lexicographic order == chronological
 * order).
 *
 * There is no `is_active` field here - it's a genuine `TripCreateRequest`/
 * `TripUpdateRequest` field, but no page in `05_PAGE_CATALOG.md`'s Create/Edit
 * Trip spec surfaces it, and the backend defaults it to `true` and never
 * reads it in any business rule (app/modules/trips/service.py) - so the form
 * simply never sends it, letting the backend's own default/existing value
 * stand, exactly as an omitted key would under `TripUpdateRequest`'s
 * partial-update semantics.
 */
export const tripFormSchema = z
  .object({
    trip_number: z.string().trim().min(1, "Trip number is required").max(50, "Must be 50 characters or fewer"),
    boat_id: z.string().trim().min(1, "Boat is required"),
    trip_type: z.enum(TRIP_TYPE_VALUES),
    status: z.enum(TRIP_STATUS_VALUES),
    captain_name: z.string().trim().max(255, "Must be 255 characters or fewer"),
    departure_port: z.string().trim().max(100, "Must be 100 characters or fewer"),
    arrival_port: z.string().trim().max(100, "Must be 100 characters or fewer"),
    departure_datetime: requiredDatetimeField,
    expected_return_datetime: optionalDatetimeField,
    actual_return_datetime: optionalDatetimeField,
    notes: z.string().trim(),
  })
  .refine(
    (values) => !values.actual_return_datetime || values.actual_return_datetime >= values.departure_datetime,
    { message: "Actual return cannot be before departure", path: ["actual_return_datetime"] }
  );

export type TripFormValues = z.infer<typeof tripFormSchema>;

export const DEFAULT_TRIP_FORM_VALUES: TripFormValues = {
  trip_number: "",
  boat_id: "",
  trip_type: "fishing",
  status: "planned",
  captain_name: "",
  departure_port: "",
  arrival_port: "",
  departure_datetime: "",
  expected_return_datetime: "",
  actual_return_datetime: "",
  notes: "",
};

function toDatetimeLocalValue(iso: string | null): string {
  if (!iso) return "";
  const parsed = parseISO(iso);
  return Number.isNaN(parsed.getTime()) ? "" : format(parsed, "yyyy-MM-dd'T'HH:mm");
}

function toIsoOrUndefined(value: string): string | undefined {
  if (!value.trim()) return undefined;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? undefined : parsed.toISOString();
}

/** Populates the form from a fetched `Trip` for the Edit page - null fields become empty strings. */
export function toTripFormValues(trip: Trip): TripFormValues {
  return {
    trip_number: trip.tripNumber,
    boat_id: trip.boatId,
    trip_type: trip.tripType,
    status: trip.status,
    captain_name: trip.captainName ?? "",
    departure_port: trip.departurePort ?? "",
    arrival_port: trip.arrivalPort ?? "",
    departure_datetime: toDatetimeLocalValue(trip.departureDatetime),
    expected_return_datetime: toDatetimeLocalValue(trip.expectedReturnDatetime),
    actual_return_datetime: toDatetimeLocalValue(trip.actualReturnDatetime),
    notes: trip.notes ?? "",
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toTripRequestPayload(values: TripFormValues): TripCreateRequest {
  return {
    boat_id: values.boat_id,
    trip_number: values.trip_number,
    trip_type: values.trip_type,
    captain_name: values.captain_name || undefined,
    departure_port: values.departure_port || undefined,
    arrival_port: values.arrival_port || undefined,
    departure_datetime: new Date(values.departure_datetime).toISOString(),
    expected_return_datetime: toIsoOrUndefined(values.expected_return_datetime),
    actual_return_datetime: toIsoOrUndefined(values.actual_return_datetime),
    status: values.status,
    notes: values.notes || undefined,
  };
}

/** Same shape as `toTripRequestPayload` - a fully-populated `TripCreateRequest` is always a valid partial `TripUpdateRequest`. */
export function toTripUpdatePayload(values: TripFormValues): TripUpdateRequest {
  return toTripRequestPayload(values);
}
