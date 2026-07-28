import { z } from "zod";

import type {
  Supplier,
  SupplierCreateRequest,
  SupplierUpdateRequest,
} from "@/features/suppliers/types/supplier";

// Mirrors the backend's exact checks (app/modules/suppliers/schemas.py) so
// the form never rejects something the backend would accept, or vice versa -
// the same three patterns `companyFormSchema` uses, since suppliers/schemas.py
// duplicates companies/schemas.py's own regexes verbatim.
const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const PHONE_PATTERN = /^\+?[0-9]{7,15}$/;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const gstinField = z
  .string()
  .trim()
  .transform((value) => value.toUpperCase())
  .refine((value) => value === "" || GSTIN_PATTERN.test(value), "Invalid GSTIN format");

const phoneField = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || PHONE_PATTERN.test(value),
    "Phone must be 7-15 digits, optionally prefixed with +"
  );

const emailField = z
  .string()
  .trim()
  .transform((value) => value.toLowerCase())
  .refine((value) => value === "" || EMAIL_PATTERN.test(value), "Enter a valid email address");

/**
 * Field names are snake_case, matching SupplierCreateRequest/
 * SupplierUpdateRequest exactly (not the client's camelCase `Supplier`
 * type) - so `mapServerErrorsToForm` can set a 422's `field_errors` directly
 * onto the right RHF field with no translation layer, mirroring
 * `companyFormSchema`.
 *
 * Scope mirrors `companyFormSchema`'s own deliberate subset: identity
 * (name, code) and contact/address fields only. There is no `status` field
 * (unlike Company's form) - the backend never accepts `status` on a
 * supplier at all (always `active` on create, server-owned thereafter, see
 * `SupplierCreateRequest`'s own docstring) - and `legal_name`/
 * `contact_person`/`credit_days`/`opening_balance` are deferred, the same
 * category of fields `companyFormSchema` itself left out of its own form.
 */
export const supplierFormSchema = z.object({
  name: z.string().trim().min(1, "Supplier name is required").max(255, "Must be 255 characters or fewer"),
  code: z.string().trim().min(1, "Supplier code is required").max(50, "Must be 50 characters or fewer"),
  gstin: gstinField,
  phone: phoneField,
  email: emailField,
  address: z.string().trim(),
  city: z.string().trim().max(100, "Must be 100 characters or fewer"),
  state: z.string().trim().max(100, "Must be 100 characters or fewer"),
  country: z.string().trim().max(100, "Must be 100 characters or fewer"),
});

export type SupplierFormValues = z.infer<typeof supplierFormSchema>;

export const DEFAULT_SUPPLIER_FORM_VALUES: SupplierFormValues = {
  name: "",
  code: "",
  gstin: "",
  phone: "",
  email: "",
  address: "",
  city: "",
  state: "",
  country: "",
};

/** Populates the form from a fetched `Supplier` for the Edit page - null fields become empty strings. */
export function toSupplierFormValues(supplier: Supplier): SupplierFormValues {
  return {
    name: supplier.name,
    code: supplier.code,
    gstin: supplier.gstin ?? "",
    phone: supplier.phone ?? "",
    email: supplier.email ?? "",
    address: supplier.address ?? "",
    city: supplier.city ?? "",
    state: supplier.state ?? "",
    country: supplier.country ?? "",
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toSupplierRequestPayload(values: SupplierFormValues): SupplierCreateRequest {
  return {
    name: values.name,
    code: values.code,
    gstin: values.gstin || undefined,
    phone: values.phone || undefined,
    email: values.email || undefined,
    address: values.address || undefined,
    city: values.city || undefined,
    state: values.state || undefined,
    country: values.country || undefined,
  };
}

/** Same shape as `toSupplierRequestPayload` - a fully-populated `SupplierCreateRequest` is always a valid partial `SupplierUpdateRequest`. */
export function toSupplierUpdatePayload(values: SupplierFormValues): SupplierUpdateRequest {
  return toSupplierRequestPayload(values);
}
