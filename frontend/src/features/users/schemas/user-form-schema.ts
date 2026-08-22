import { z } from "zod";

import type {
  ManagedUser,
  UserCreateRequest,
  UserPasswordResetRequest,
  UserUpdateRequest,
} from "@/features/users/types/user";

// Mirrors the backend's exact checks (app/modules/users/schemas.py,
// app/modules/auth/security.py's password_policy_violations) so the form
// never rejects something the backend would accept, or vice versa.
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PHONE_PATTERN = /^\+?[0-9]{7,15}$/;
const USERNAME_PATTERN = /^[a-zA-Z0-9_.-]{3,100}$/;
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

const phoneField = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || PHONE_PATTERN.test(value),
    "Phone must be 7-15 digits, optionally prefixed with +"
  );

export const passwordField = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .refine((value) => /[A-Z]/.test(value), "Password must contain an uppercase letter")
  .refine((value) => /[a-z]/.test(value), "Password must contain a lowercase letter")
  .refine((value) => /[0-9]/.test(value), "Password must contain a number")
  .refine((value) => SPECIAL_CHAR_PATTERN.test(value), "Password must contain a special character");

/**
 * Field names are snake_case, matching UserCreateRequest exactly (not the
 * client's camelCase `ManagedUser` type) - same rationale as
 * company-form-schema.ts, so `mapServerErrorsToForm` needs no translation
 * layer. No `is_superuser` or `status` field - neither is ever set through
 * this form (see UserCreateRequest's own doc comment).
 */
export const userCreateFormSchema = z.object({
  full_name: z.string().trim().min(1, "Full name is required").max(255, "Must be 255 characters or fewer"),
  email: emailField,
  username: usernameField,
  phone: phoneField,
  password: passwordField,
  role_id: z.string().min(1, "Role is required"),
});

export type UserCreateFormValues = z.infer<typeof userCreateFormSchema>;

export const DEFAULT_USER_CREATE_FORM_VALUES: UserCreateFormValues = {
  full_name: "",
  email: "",
  username: "",
  phone: "",
  password: "",
  role_id: "",
};

export function toUserCreateRequestPayload(values: UserCreateFormValues): UserCreateRequest {
  return {
    full_name: values.full_name,
    email: values.email,
    username: values.username,
    phone: values.phone || undefined,
    password: values.password,
    role_id: values.role_id,
  };
}

/** No password field here - an admin-triggered reset is a separate action,
 * PATCH /users/{id}/password (see userPasswordResetFormSchema below), not
 * part of this identity/role edit. */
export const userEditFormSchema = z.object({
  full_name: z.string().trim().min(1, "Full name is required").max(255, "Must be 255 characters or fewer"),
  email: emailField,
  username: usernameField,
  phone: phoneField,
  role_id: z.string().min(1, "Role is required"),
});

export type UserEditFormValues = z.infer<typeof userEditFormSchema>;

/** Populates the form from a fetched `ManagedUser` for the Edit page. */
export function toUserEditFormValues(user: ManagedUser): UserEditFormValues {
  return {
    full_name: user.fullName,
    email: user.email,
    username: user.username,
    phone: user.phone ?? "",
    role_id: user.role?.id ?? "",
  };
}

export function toUserUpdatePayload(values: UserEditFormValues): UserUpdateRequest {
  return {
    full_name: values.full_name,
    email: values.email,
    username: values.username,
    phone: values.phone || undefined,
    role_id: values.role_id,
  };
}

/**
 * PATCH /users/{id}/password: an admin sets the target's new password
 * directly (same shape as PATCH /users/{id}/status - a small, single-
 * purpose action, not a full form). `confirm_password` never leaves the
 * browser - it exists only so a typo doesn't silently reset someone's
 * account to a password the admin didn't mean to type.
 */
export const userPasswordResetFormSchema = z
  .object({
    new_password: passwordField,
    confirm_password: z.string().min(1, "Please confirm the new password"),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type UserPasswordResetFormValues = z.infer<typeof userPasswordResetFormSchema>;

export const DEFAULT_USER_PASSWORD_RESET_FORM_VALUES: UserPasswordResetFormValues = {
  new_password: "",
  confirm_password: "",
};

export function toUserPasswordResetPayload(
  values: UserPasswordResetFormValues
): UserPasswordResetRequest {
  return { new_password: values.new_password };
}
