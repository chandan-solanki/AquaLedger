import { z } from "zod";

import type { ChangePasswordRequest } from "@/features/profile/types/profile";

/**
 * Client-side validation stays intentionally minimal - required fields,
 * a length floor, and confirmation match. The full password policy
 * (upper/lower/digit/special, app/modules/auth/security.py's
 * password_policy_violations) is NOT duplicated here: the backend is the
 * authority on that, returns it as 422 field_errors on `new_password`,
 * and the policy could change server-side without this form drifting out
 * of sync (Sprint 16 Session 3).
 */
export const changePasswordFormSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "Password must be at least 8 characters long"),
    confirm_password: z.string().min(1, "Please confirm your new password"),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type ChangePasswordFormValues = z.infer<typeof changePasswordFormSchema>;

export const DEFAULT_CHANGE_PASSWORD_FORM_VALUES: ChangePasswordFormValues = {
  current_password: "",
  new_password: "",
  confirm_password: "",
};

/** Drops `confirm_password` - it never leaves the browser. */
export function toChangePasswordPayload(values: ChangePasswordFormValues): ChangePasswordRequest {
  return {
    current_password: values.current_password,
    new_password: values.new_password,
  };
}
