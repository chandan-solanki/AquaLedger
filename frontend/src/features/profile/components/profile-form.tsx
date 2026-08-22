"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormActions, FormField, FormGrid, PhoneInput } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DEFAULT_PROFILE_FORM_VALUES,
  profileFormSchema,
  type ProfileFormValues,
} from "@/features/profile/schemas/profile-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface ProfileFormProps {
  defaultValues: ProfileFormValues;
  onSubmit: (values: ProfileFormValues) => Promise<void>;
  disabled?: boolean;
}

/**
 * The editable half of My Profile - full name, username, phone. Owns its
 * own submit try/catch the same way CompanyProfileForm does: a 409
 * (duplicate username) or any other non-field error surfaces as a toast,
 * a 422 field_errors response maps onto the matching field.
 */
export function ProfileForm({ defaultValues, onSubmit, disabled = false }: ProfileFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: defaultValues ?? DEFAULT_PROFILE_FORM_VALUES,
  });

  async function handleFormSubmit(values: ProfileFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<ProfileFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  const isReadOnly = disabled || isSubmitting;

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormGrid columns={2}>
        <FormField label="Full Name" required error={errors.full_name?.message} className="md:col-span-full">
          {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
            <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("full_name")} />
          )}
        </FormField>

        <FormField label="Username" required error={errors.username?.message}>
          {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
            <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("username")} />
          )}
        </FormField>

        <PhoneInput label="Phone" error={errors.phone?.message} disabled={isReadOnly} {...register("phone")} />
      </FormGrid>

      <FormActions
        secondary={
          <Button type="button" variant="outline" onClick={() => reset(defaultValues)} disabled={isReadOnly || !isDirty}>
            Reset
          </Button>
        }
        primary={
          <Button type="submit" disabled={isReadOnly}>
            {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
            {isSubmitting ? "Saving…" : "Save Changes"}
          </Button>
        }
      />
    </form>
  );
}
