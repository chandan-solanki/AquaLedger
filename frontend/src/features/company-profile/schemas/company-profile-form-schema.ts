import { z } from "zod";

import type {
  CompanyProfile,
  CompanyProfileUpdateRequest,
} from "@/features/company-profile/types/company-profile";

// Mirrors the backend's exact checks (app/modules/company_profile/schemas.py)
// so the form never rejects something the backend would accept, or vice
// versa - duplicated rather than imported, same convention
// company-form-schema.ts already establishes (no shared regex module exists
// in this codebase).
const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const PAN_PATTERN = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const PHONE_PATTERN = /^\+?[0-9]{7,15}$/;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const gstinField = z
  .string()
  .trim()
  .transform((value) => value.toUpperCase())
  .refine((value) => value === "" || GSTIN_PATTERN.test(value), "Invalid GSTIN format");

const panField = z
  .string()
  .trim()
  .transform((value) => value.toUpperCase())
  .refine((value) => value === "" || PAN_PATTERN.test(value), "Invalid PAN format");

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

export const companyProfileFormSchema = z.object({
  legal_name: z.string().trim().min(1, "Legal name is required").max(255, "Must be 255 characters or fewer"),
  display_name: z.string().trim().max(255, "Must be 255 characters or fewer"),
  company_code: z.string().trim().max(50, "Must be 50 characters or fewer"),
  phone: phoneField,
  alt_phone: phoneField,
  email: emailField,
  website: z.string().trim().max(255, "Must be 255 characters or fewer"),
  address_line1: z.string().trim().max(255, "Must be 255 characters or fewer"),
  address_line2: z.string().trim().max(255, "Must be 255 characters or fewer"),
  city: z.string().trim().max(100, "Must be 100 characters or fewer"),
  state: z.string().trim().max(100, "Must be 100 characters or fewer"),
  state_code: z.string().trim().max(2, "Must be 2 characters or fewer"),
  pincode: z.string().trim().max(10, "Must be 10 characters or fewer"),
  country: z.string().trim().max(100, "Must be 100 characters or fewer"),
  gstin: gstinField,
  pan: panField,
});

export type CompanyProfileFormValues = z.infer<typeof companyProfileFormSchema>;

export const DEFAULT_COMPANY_PROFILE_FORM_VALUES: CompanyProfileFormValues = {
  legal_name: "",
  display_name: "",
  company_code: "",
  phone: "",
  alt_phone: "",
  email: "",
  website: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  state_code: "",
  pincode: "",
  country: "",
  gstin: "",
  pan: "",
};

/** Populates the form from a fetched `CompanyProfile` - null fields become empty strings. */
export function toCompanyProfileFormValues(profile: CompanyProfile): CompanyProfileFormValues {
  return {
    legal_name: profile.legalName,
    display_name: profile.displayName ?? "",
    company_code: profile.companyCode ?? "",
    phone: profile.phone ?? "",
    alt_phone: profile.altPhone ?? "",
    email: profile.email ?? "",
    website: profile.website ?? "",
    address_line1: profile.addressLine1 ?? "",
    address_line2: profile.addressLine2 ?? "",
    city: profile.city ?? "",
    state: profile.state ?? "",
    state_code: profile.stateCode ?? "",
    pincode: profile.pincode ?? "",
    country: profile.country ?? "",
    gstin: profile.gstin ?? "",
    pan: profile.pan ?? "",
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend leaves the existing value untouched (a partial update) rather than overwriting it with an empty string. */
export function toCompanyProfileUpdatePayload(
  values: CompanyProfileFormValues
): CompanyProfileUpdateRequest {
  return {
    legal_name: values.legal_name,
    display_name: values.display_name || undefined,
    company_code: values.company_code || undefined,
    phone: values.phone || undefined,
    alt_phone: values.alt_phone || undefined,
    email: values.email || undefined,
    website: values.website || undefined,
    address_line1: values.address_line1 || undefined,
    address_line2: values.address_line2 || undefined,
    city: values.city || undefined,
    state: values.state || undefined,
    state_code: values.state_code || undefined,
    pincode: values.pincode || undefined,
    country: values.country || undefined,
    gstin: values.gstin || undefined,
    pan: values.pan || undefined,
  };
}
