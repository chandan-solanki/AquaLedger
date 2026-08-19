"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { EmailInput, FormActions, FormField, FormGrid, FormSection, PhoneInput, SearchableSelect } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRoleOptions } from "@/features/users/hooks/use-role-options";
import { userEditFormSchema, type UserEditFormValues } from "@/features/users/schemas/user-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface UserEditFormProps {
  defaultValues: UserEditFormValues;
  onSubmit: (values: UserEditFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The Edit User form - identity fields plus role reassignment. No password
 * field (admin-triggered password resets aren't supported by the existing
 * architecture - see UserUpdateRequest's doc comment) and no status field
 * (that's PATCH /users/{id}/status's own Activate/Deactivate action, kept
 * out of this form so a role edit can never accidentally change status).
 */
export function UserEditForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save Changes" }: UserEditFormProps) {
  const roleOptionsQuery = useRoleOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<UserEditFormValues>({
    resolver: zodResolver(userEditFormSchema),
    defaultValues,
  });

  async function handleFormSubmit(values: UserEditFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<UserEditFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  // The currently-assigned role must always be selectable even if it's
  // super_admin and the caller isn't themselves a superuser - the backend's
  // list_role_options excludes super_admin from the picker in that case, but
  // re-submitting the form unchanged must not silently drop the existing
  // role_id (the backend independently blocks an actual change away from it
  // for a non-superuser via SUPER_ADMIN_ROLE_PROTECTED).
  const fetchedRoleOptions = roleOptionsQuery.data ?? [];
  const currentRoleId = defaultValues.role_id;
  const hasCurrentRole = fetchedRoleOptions.some((role) => role.id === currentRoleId);
  const roleOptions = (
    hasCurrentRole || !currentRoleId
      ? fetchedRoleOptions
      : [{ id: currentRoleId, name: "Current role", description: null }, ...fetchedRoleOptions]
  ).map((role) => ({
    value: role.id,
    label: role.name,
    description: role.description ?? undefined,
  }));

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Identity">
        <FormGrid columns={2}>
          <FormField label="Full Name" required error={errors.full_name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("full_name")} />
            )}
          </FormField>

          <FormField label="Username" required error={errors.username?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("username")} />
            )}
          </FormField>

          <EmailInput label="Email" required error={errors.email?.message} {...register("email")} />

          <PhoneInput label="Phone" error={errors.phone?.message} {...register("phone")} />

          <SearchableSelect
            label="Role"
            required
            options={roleOptions}
            value={watch("role_id")}
            onChange={(value) => value && setValue("role_id", value, { shouldValidate: true })}
            error={errors.role_id?.message}
            disabled={roleOptionsQuery.isLoading}
            placeholder={roleOptionsQuery.isLoading ? "Loading roles…" : "Select a role…"}
          />
        </FormGrid>
      </FormSection>

      <FormActions
        secondary={
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        }
        primary={
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
            {isSubmitting ? "Saving…" : submitLabel}
          </Button>
        }
      />
    </form>
  );
}
