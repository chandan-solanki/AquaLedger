import { z } from "zod";

import { toBoatStatus } from "@/features/boats/constants/boat-status";
import type { BoatStatus } from "@/features/boats/constants/boat-status";
import type { Boat, BoatCreateRequest, BoatUpdateRequest } from "@/features/boats/types/boat";

// Mirrors the backend's exact checks (app/modules/boats/schemas.py) so the
// form never rejects something the backend would accept, or vice versa.
const PHONE_PATTERN = /^\+?[0-9]{7,15}$/;
// capacity_kg: Decimal, max_digits=12, decimal_places=3, ge=0.
const CAPACITY_PATTERN = /^\d{1,9}(\.\d{1,3})?$/;
// engine_hp: int, ge=0.
const ENGINE_HP_PATTERN = /^\d{1,9}$/;

const phoneField = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || PHONE_PATTERN.test(value),
    "Phone must be 7-15 digits, optionally prefixed with +"
  );

const capacityField = z
  .string()
  .trim()
  .refine((value) => value === "" || CAPACITY_PATTERN.test(value), "Enter a valid capacity (up to 3 decimal places)");

const engineHpField = z
  .string()
  .trim()
  .refine((value) => value === "" || ENGINE_HP_PATTERN.test(value), "Enter a whole number of 0 or more");

/**
 * Field names are snake_case, matching BoatCreateRequest/BoatUpdateRequest
 * exactly (not the client's camelCase `Boat` type) - so `mapServerErrorsToForm`
 * can set a 422's `field_errors` directly onto the right RHF field with no
 * translation layer, mirroring `fishFormSchema`.
 *
 * `status` is the one exception: the backend has no `status` field, only
 * `is_active` (boolean). The form keeps the same "Status" select UX as
 * Fish/Companies and converts it to `is_active` only at the payload boundary
 * (`toBoatRequestPayload`).
 *
 * `insurance_expiry`/`license_expiry` are kept as ISO date strings
 * (`yyyy-MM-dd`) here rather than `Date` objects - `BoatForm` converts to/from
 * `Date` at the `DatePicker` boundary, and the string is what ships straight
 * through to the backend's `date` fields unmodified.
 *
 * There is no `company_id` field - a boat is owned by the tenant only. A
 * `Company` is a customer (buyer), never a boat owner (ARCHITECTURE.md's
 * Business Model).
 */
export const boatFormSchema = z.object({
  code: z.string().trim().min(1, "Boat code is required").max(50, "Must be 50 characters or fewer"),
  name: z.string().trim().min(1, "Boat name is required").max(255, "Must be 255 characters or fewer"),
  registration_number: z
    .string()
    .trim()
    .min(1, "Registration number is required")
    .max(50, "Must be 50 characters or fewer"),
  license_number: z.string().trim().max(50, "Must be 50 characters or fewer"),
  boat_type: z.string().trim().max(50, "Must be 50 characters or fewer"),
  capacity_kg: capacityField,
  engine_number: z.string().trim().max(50, "Must be 50 characters or fewer"),
  engine_hp: engineHpField,
  captain_name: z.string().trim().max(255, "Must be 255 characters or fewer"),
  captain_phone: phoneField,
  insurance_expiry: z.string().trim(),
  license_expiry: z.string().trim(),
  notes: z.string().trim(),
  status: z.enum(["active", "inactive"]),
});

export type BoatFormValues = z.infer<typeof boatFormSchema>;

export const DEFAULT_BOAT_FORM_VALUES: BoatFormValues = {
  code: "",
  name: "",
  registration_number: "",
  license_number: "",
  boat_type: "",
  capacity_kg: "",
  engine_number: "",
  engine_hp: "",
  captain_name: "",
  captain_phone: "",
  insurance_expiry: "",
  license_expiry: "",
  notes: "",
  status: "active",
};

/** Populates the form from a fetched `Boat` for the Edit page - null fields become empty strings. */
export function toBoatFormValues(boat: Boat): BoatFormValues {
  return {
    code: boat.code,
    name: boat.name,
    registration_number: boat.registrationNumber,
    license_number: boat.licenseNumber ?? "",
    boat_type: boat.boatType ?? "",
    capacity_kg: boat.capacityKg ?? "",
    engine_number: boat.engineNumber ?? "",
    engine_hp: boat.engineHp != null ? String(boat.engineHp) : "",
    captain_name: boat.captainName ?? "",
    captain_phone: boat.captainPhone ?? "",
    insurance_expiry: boat.insuranceExpiry ?? "",
    license_expiry: boat.licenseExpiry ?? "",
    notes: boat.notes ?? "",
    status: toBoatStatus(boat.isActive),
  };
}

function toStatusBoolean(status: BoatStatus): boolean {
  return status === "active";
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toBoatRequestPayload(values: BoatFormValues): BoatCreateRequest {
  return {
    code: values.code,
    name: values.name,
    registration_number: values.registration_number,
    license_number: values.license_number || undefined,
    boat_type: values.boat_type || undefined,
    capacity_kg: values.capacity_kg || undefined,
    engine_number: values.engine_number || undefined,
    engine_hp: values.engine_hp ? Number(values.engine_hp) : undefined,
    captain_name: values.captain_name || undefined,
    captain_phone: values.captain_phone || undefined,
    insurance_expiry: values.insurance_expiry || undefined,
    license_expiry: values.license_expiry || undefined,
    notes: values.notes || undefined,
    is_active: toStatusBoolean(values.status),
  };
}

/** Same shape as `toBoatRequestPayload` - a fully-populated `BoatCreateRequest` is always a valid partial `BoatUpdateRequest`. */
export function toBoatUpdatePayload(values: BoatFormValues): BoatUpdateRequest {
  return toBoatRequestPayload(values);
}
