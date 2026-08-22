import { z } from "zod";

import type { User } from "@/features/auth/types/auth";
import type { ProfileUpdateRequest } from "@/features/profile/types/profile";

// Mirrors the backend's exact checks (app/modules/profile/schemas.py,
// app/modules/users/schemas.py) so the form never rejects something the
// backend would accept, or vice versa - duplicated rather than imported,
// same convention company-profile-form-schema.ts already establishes (no
// shared regex module exists in this codebase).
const USERNAME_PATTERN = /^[a-zA-Z0-9_.-]{3,100}$/;
const PHONE_PATTERN = /^\+?[0-9]{7,15}$/;

export const profileFormSchema = z.object({
  full_name: z.string().trim().min(1, "Full name is required").max(255, "Must be 255 characters or fewer"),
  username: z
    .string()
    .trim()
    .toLowerCase()
    .refine(
      (value) => USERNAME_PATTERN.test(value),
      "Username must be 3-100 characters: letters, numbers, dot, underscore or hyphen"
    ),
  phone: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || PHONE_PATTERN.test(value),
      "Phone must be 7-15 digits, optionally prefixed with +"
    ),
});

export type ProfileFormValues = z.infer<typeof profileFormSchema>;

export const DEFAULT_PROFILE_FORM_VALUES: ProfileFormValues = {
  full_name: "",
  username: "",
  phone: "",
};

/** Populates the form from the current session's `User` - null phone becomes an empty string. */
export function toProfileFormValues(user: User): ProfileFormValues {
  return {
    full_name: user.fullName,
    username: user.username,
    phone: user.phone ?? "",
  };
}

/** Maps form values onto the request payload - an empty phone becomes `undefined` (unchanged) rather than clearing it, matching CompanyProfileForm's own convention. full_name/username are always sent since this form never lets them be blank. */
export function toProfileUpdatePayload(values: ProfileFormValues): ProfileUpdateRequest {
  return {
    full_name: values.full_name,
    username: values.username,
    phone: values.phone || undefined,
  };
}
