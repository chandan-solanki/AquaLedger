"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/form";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  DEFAULT_USER_PASSWORD_RESET_FORM_VALUES,
  userPasswordResetFormSchema,
  type UserPasswordResetFormValues,
} from "@/features/users/schemas/user-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface ResetPasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userName: string;
  onSubmit: (values: UserPasswordResetFormValues) => Promise<void>;
}

/**
 * A plain Dialog, not ConfirmationDialog - this action needs two password
 * inputs, not a yes/no decision, so it follows the "form inside a modal"
 * shape rather than the base confirmation pattern. A wrong/weak new
 * password comes back from the backend as a 422 field_errors.new_password,
 * mapped onto the field the same way ProfileForm/ChangePasswordForm do;
 * the "cannot reset your own password" and "requires a superuser" business
 * rules aren't field-specific, so they fall through to a toast instead.
 */
export function ResetPasswordDialog({
  open,
  onOpenChange,
  userName,
  onSubmit,
}: ResetPasswordDialogProps) {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<UserPasswordResetFormValues>({
    resolver: zodResolver(userPasswordResetFormSchema),
    defaultValues: DEFAULT_USER_PASSWORD_RESET_FORM_VALUES,
  });

  async function handleFormSubmit(values: UserPasswordResetFormValues) {
    try {
      await onSubmit(values);
      reset(DEFAULT_USER_PASSWORD_RESET_FORM_VALUES);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<UserPasswordResetFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (isSubmitting) return;
    if (!nextOpen) reset(DEFAULT_USER_PASSWORD_RESET_FORM_VALUES);
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit(handleFormSubmit)} noValidate>
          <DialogHeader>
            <DialogTitle>Reset password for {userName}</DialogTitle>
            <DialogDescription>
              They will be signed out everywhere and must sign in with this new password, which
              they will be required to change again on their next login.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <FormField label="New Password" required error={errors.new_password?.message}>
              {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
                <Input
                  id={id}
                  type="password"
                  autoComplete="new-password"
                  aria-describedby={describedBy}
                  aria-invalid={ariaInvalid}
                  disabled={isSubmitting}
                  {...register("new_password")}
                />
              )}
            </FormField>

            <FormField
              label="Confirm New Password"
              required
              error={errors.confirm_password?.message}
            >
              {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
                <Input
                  id={id}
                  type="password"
                  autoComplete="new-password"
                  aria-describedby={describedBy}
                  aria-invalid={ariaInvalid}
                  disabled={isSubmitting}
                  {...register("confirm_password")}
                />
              )}
            </FormField>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
              {isSubmitting ? "Resetting…" : "Reset Password"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
