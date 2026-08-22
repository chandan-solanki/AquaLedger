"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormActions, FormField } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  changePasswordFormSchema,
  DEFAULT_CHANGE_PASSWORD_FORM_VALUES,
  type ChangePasswordFormValues,
} from "@/features/profile/schemas/password-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface ChangePasswordFormProps {
  onSubmit: (values: ChangePasswordFormValues) => Promise<void>;
  disabled?: boolean;
}

/**
 * Talks to the existing POST /auth/change-password through the /profile
 * BFF proxy (via the page's onSubmit) - this component only owns the
 * form's own fields, validation and error mapping, same division of
 * responsibility as ProfileForm.
 *
 * A wrong current_password comes back as a 401 INVALID_CREDENTIALS, not a
 * 422 field error (the backend never reveals *which* field failed via the
 * generic field_errors path for this one check) - mapped onto the Current
 * Password field explicitly so it reads like any other inline validation
 * error instead of a generic toast.
 */
export function ChangePasswordForm({ onSubmit, disabled = false }: ChangePasswordFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordFormSchema),
    defaultValues: DEFAULT_CHANGE_PASSWORD_FORM_VALUES,
  });

  async function handleFormSubmit(values: ChangePasswordFormValues) {
    try {
      await onSubmit(values);
      reset(DEFAULT_CHANGE_PASSWORD_FORM_VALUES);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.code === "INVALID_CREDENTIALS") {
        setError("current_password", { type: "server", message: "Current password is incorrect." });
        return;
      }
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<ChangePasswordFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  const isReadOnly = disabled || isSubmitting;

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          label="Current Password"
          required
          error={errors.current_password?.message}
          className="sm:col-span-full sm:max-w-sm"
        >
          {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
            <Input
              id={id}
              type="password"
              autoComplete="current-password"
              aria-describedby={describedBy}
              aria-invalid={ariaInvalid}
              disabled={isReadOnly}
              {...register("current_password")}
            />
          )}
        </FormField>

        <FormField label="New Password" required error={errors.new_password?.message}>
          {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
            <Input
              id={id}
              type="password"
              autoComplete="new-password"
              aria-describedby={describedBy}
              aria-invalid={ariaInvalid}
              disabled={isReadOnly}
              {...register("new_password")}
            />
          )}
        </FormField>

        <FormField
          label="Confirm New Password"
          required
          error={errors.confirm_password?.message}
          description="At least 8 characters, with an uppercase and lowercase letter, a number, and a special character."
        >
          {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
            <Input
              id={id}
              type="password"
              autoComplete="new-password"
              aria-describedby={describedBy}
              aria-invalid={ariaInvalid}
              disabled={isReadOnly}
              {...register("confirm_password")}
            />
          )}
        </FormField>
      </div>

      <FormActions
        primary={
          <Button type="submit" disabled={isReadOnly}>
            {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
            {isSubmitting ? "Changing…" : "Change Password"}
          </Button>
        }
      />
    </form>
  );
}
