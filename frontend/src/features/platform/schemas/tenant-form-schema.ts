import { z } from "zod";

import type { TenantCreateRequest } from "@/features/platform/types/tenant";

// Mirrors the backend's exact checks (app/modules/platform_admin/schemas.py,
// app/modules/auth/security.py's password_policy_violations) so the form
// never rejects something the backend would accept, or vice versa.
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const USERNAME_PATTERN = /^[a-zA-Z0-9_.-]{3,100}$/;
const SLUG_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const SPECIAL_CHAR_PATTERN = /[!@#$%^&*()_+\-=[\]{};:'"\\|,.<>/?`~]/;

const emailField = z
  .string()
  .trim()
  .min(1, "Email is required")
  .transform((value) => value.toLowerCase())
  .refine((value) => EMAIL_PATTERN.test(value), "Enter a valid email address");

const usernameField = z
  .string()
  .trim()
  .min(1, "Username is required")
  .transform((value) => value.toLowerCase())
  .refine(
    (value) => USERNAME_PATTERN.test(value),
    "3-100 characters: letters, numbers, dot, underscore or hyphen"
  );

const passwordField = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .refine((value) => /[A-Z]/.test(value), "Password must contain an uppercase letter")
  .refine((value) => /[a-z]/.test(value), "Password must contain a lowercase letter")
  .refine((value) => /[0-9]/.test(value), "Password must contain a number")
  .refine((value) => SPECIAL_CHAR_PATTERN.test(value), "Password must contain a special character");

/**
 * Field names mirror TenantCreateRequest exactly, including the nested
 * `administrator` object - not flattened - so a 422's
 * `field_errors["administrator.password"]` (see TenantService.create_tenant's
 * password-policy check) maps straight onto `errors.administrator?.password`
 * via `mapServerErrorsToForm` with no translation layer, same rationale as
 * company-form-schema.ts/user-form-schema.ts's flat cases.
 *
 * `confirm_password` is a sibling, frontend-only field - it is never part of
 * TenantCreateRequest and is stripped by `toTenantCreateRequestPayload`.
 */
export const tenantFormSchema = z
  .object({
    name: z.string().trim().min(1, "Tenant name is required").max(255, "Must be 255 characters or fewer"),
    slug: z
      .string()
      .trim()
      .toLowerCase()
      .min(1, "Slug is required")
      .max(100, "Must be 100 characters or fewer")
      .refine(
        (value) => SLUG_PATTERN.test(value),
        "Slug must be lowercase letters, numbers and single hyphens only (e.g. 'ocean-fresh-traders')"
      ),
    administrator: z.object({
      full_name: z.string().trim().min(1, "Full name is required").max(255, "Must be 255 characters or fewer"),
      email: emailField,
      username: usernameField,
      password: passwordField,
    }),
    confirm_password: z.string().min(1, "Please confirm the password"),
  })
  .refine((values) => values.administrator.password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type TenantFormValues = z.infer<typeof tenantFormSchema>;

export const DEFAULT_TENANT_FORM_VALUES: TenantFormValues = {
  name: "",
  slug: "",
  administrator: {
    full_name: "",
    email: "",
    username: "",
    password: "",
  },
  confirm_password: "",
};

/** Strips the frontend-only `confirm_password` field - never sent to the backend. */
export function toTenantCreateRequestPayload(values: TenantFormValues): TenantCreateRequest {
  return {
    name: values.name,
    slug: values.slug,
    administrator: {
      email: values.administrator.email,
      username: values.administrator.username,
      full_name: values.administrator.full_name,
      password: values.administrator.password,
    },
  };
}
