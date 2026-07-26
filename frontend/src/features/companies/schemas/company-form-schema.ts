import { z } from "zod";

import type {
  Company,
  CompanyCreateRequest,
  CompanyUpdateRequest,
} from "@/features/companies/types/company";

// Mirrors the backend's exact checks (app/modules/companies/schemas.py) so
// the form never rejects something the backend would accept, or vice versa.
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
 * Field names are snake_case, matching CompanyCreateRequest/
 * CompanyUpdateRequest exactly (not the client's camelCase `Company` type) -
 * so `mapServerErrorsToForm` can set a 422's `field_errors` directly onto
 * the right RHF field with no translation layer, and the submitted values
 * need no remapping to become the request payload.
 *
 * `company_type` isn't in this session's stated field list, but the backend
 * requires it on create (CompanyCreateRequest.company_type has no default) -
 * omitting it would make every submission fail with a 422, so it's included
 * here as a required select, defaulting to "customer".
 */
export const companyFormSchema = z.object({
  name: z.string().trim().min(1, "Company name is required").max(255, "Must be 255 characters or fewer"),
  code: z.string().trim().min(1, "Company code is required").max(50, "Must be 50 characters or fewer"),
  company_type: z.enum(["customer", "supplier", "both"]),
  status: z.enum(["active", "inactive"]),
  gstin: gstinField,
  phone: phoneField,
  email: emailField,
  address_line1: z.string().trim().max(255, "Must be 255 characters or fewer"),
  city: z.string().trim().max(100, "Must be 100 characters or fewer"),
  state: z.string().trim().max(100, "Must be 100 characters or fewer"),
  country: z.string().trim().max(100, "Must be 100 characters or fewer"),
  pincode: z.string().trim().max(10, "Must be 10 characters or fewer"),
  notes: z.string().trim(),
});

export type CompanyFormValues = z.infer<typeof companyFormSchema>;

export const DEFAULT_COMPANY_FORM_VALUES: CompanyFormValues = {
  name: "",
  code: "",
  company_type: "customer",
  status: "active",
  gstin: "",
  phone: "",
  email: "",
  address_line1: "",
  city: "",
  state: "",
  country: "",
  pincode: "",
  notes: "",
};

/** Populates the form from a fetched `Company` for the Edit page - null fields become empty strings. */
export function toCompanyFormValues(company: Company): CompanyFormValues {
  return {
    name: company.name,
    code: company.code,
    company_type: company.companyType,
    status: company.status,
    gstin: company.gstin ?? "",
    phone: company.phone ?? "",
    email: company.email ?? "",
    address_line1: company.addressLine1 ?? "",
    city: company.city ?? "",
    state: company.state ?? "",
    country: company.country ?? "",
    pincode: company.pincode ?? "",
    notes: company.notes ?? "",
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toCompanyRequestPayload(values: CompanyFormValues): CompanyCreateRequest {
  return {
    name: values.name,
    code: values.code,
    company_type: values.company_type,
    status: values.status,
    gstin: values.gstin || undefined,
    phone: values.phone || undefined,
    email: values.email || undefined,
    address_line1: values.address_line1 || undefined,
    city: values.city || undefined,
    state: values.state || undefined,
    country: values.country || undefined,
    pincode: values.pincode || undefined,
    notes: values.notes || undefined,
  };
}

/** Same shape as `toCompanyRequestPayload` - a fully-populated `CompanyCreateRequest` is always a valid partial `CompanyUpdateRequest`. */
export function toCompanyUpdatePayload(values: CompanyFormValues): CompanyUpdateRequest {
  return toCompanyRequestPayload(values);
}
