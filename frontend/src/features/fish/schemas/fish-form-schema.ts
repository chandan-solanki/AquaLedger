import { z } from "zod";

import { toFishStatus } from "@/features/fish/constants/fish-status";
import type { FishStatus } from "@/features/fish/constants/fish-status";
import type { Fish, FishCreateRequest, FishUpdateRequest } from "@/features/fish/types/fish";

// Mirrors the backend's exact checks (app/modules/fish/schemas.py) so the
// form never rejects something the backend would accept, or vice versa.
const HSN_PATTERN = /^[0-9]{4,8}$/;
const RATE_PATTERN = /^\d{1,8}(\.\d{1,4})?$/;

const hsnCodeField = z
  .string()
  .trim()
  .refine((value) => value === "" || HSN_PATTERN.test(value), "HSN code must be 4, 6 or 8 digits");

const rateField = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || RATE_PATTERN.test(value),
    "Enter a valid rate (up to 4 decimal places)"
  );

/**
 * Field names are snake_case, matching FishCreateRequest/FishUpdateRequest
 * exactly (not the client's camelCase `Fish` type) - so `mapServerErrorsToForm`
 * can set a 422's `field_errors` directly onto the right RHF field with no
 * translation layer, mirroring `companyFormSchema`.
 *
 * `status` is the one exception: the backend has no `status` field, only
 * `is_active` (boolean). The form keeps the same "Status" select UX as
 * Companies (`FISH_STATUS_OPTIONS`) and converts it to `is_active` only at
 * the payload boundary (`toFishRequestPayload`), since a boolean has no
 * server-side field errors worth mapping back onto anyway.
 */
export const fishFormSchema = z.object({
  code: z.string().trim().min(1, "Fish code is required").max(50, "Must be 50 characters or fewer"),
  name: z.string().trim().min(1, "Fish name is required").max(255, "Must be 255 characters or fewer"),
  local_name: z.string().trim().max(255, "Must be 255 characters or fewer"),
  scientific_name: z.string().trim().max(255, "Must be 255 characters or fewer"),
  category: z.string().trim().max(100, "Must be 100 characters or fewer"),
  unit: z.enum(["kg", "box", "piece", "ton"]),
  default_purchase_rate: rateField,
  default_sale_rate: rateField,
  hsn_code: hsnCodeField,
  description: z.string().trim(),
  status: z.enum(["active", "inactive"]),
});

export type FishFormValues = z.infer<typeof fishFormSchema>;

export const DEFAULT_FISH_FORM_VALUES: FishFormValues = {
  code: "",
  name: "",
  local_name: "",
  scientific_name: "",
  category: "",
  unit: "kg",
  default_purchase_rate: "",
  default_sale_rate: "",
  hsn_code: "",
  description: "",
  status: "active",
};

/** Populates the form from a fetched `Fish` for the Edit page - null fields become empty strings. */
export function toFishFormValues(fish: Fish): FishFormValues {
  return {
    code: fish.code,
    name: fish.name,
    local_name: fish.localName ?? "",
    scientific_name: fish.scientificName ?? "",
    category: fish.category ?? "",
    unit: fish.unit,
    default_purchase_rate: fish.defaultPurchaseRate ?? "",
    default_sale_rate: fish.defaultSaleRate ?? "",
    hsn_code: fish.hsnCode ?? "",
    description: fish.description ?? "",
    status: toFishStatus(fish.isActive),
  };
}

function toStatusBoolean(status: FishStatus): boolean {
  return status === "active";
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toFishRequestPayload(values: FishFormValues): FishCreateRequest {
  return {
    code: values.code,
    name: values.name,
    local_name: values.local_name || undefined,
    scientific_name: values.scientific_name || undefined,
    category: values.category || undefined,
    unit: values.unit,
    default_purchase_rate: values.default_purchase_rate || undefined,
    default_sale_rate: values.default_sale_rate || undefined,
    hsn_code: values.hsn_code || undefined,
    description: values.description || undefined,
    is_active: toStatusBoolean(values.status),
  };
}

/** Same shape as `toFishRequestPayload` - a fully-populated `FishCreateRequest` is always a valid partial `FishUpdateRequest`. */
export function toFishUpdatePayload(values: FishFormValues): FishUpdateRequest {
  return toFishRequestPayload(values);
}
