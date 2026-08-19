"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { EmailInput, FormActions, FormField, FormGrid, FormSection, PhoneInput, SearchableSelect } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRoleOptions } from "@/features/users/hooks/use-role-options";
import {
  DEFAULT_USER_CREATE_FORM_VALUES,
  userCreateFormSchema,
  type UserCreateFormValues,
} from "@/features/users/schemas/user-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface UserCreateFormProps {
  onSubmit: (values: UserCreateFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The Create User form. Unlike Company's shared Create/Edit form, this one
 * is Create-only - a password field belongs here (the account's initial,
 * admin-set password, per this session's no-invitation-flow decision) but
 * has no place in Edit, where role reassignment is the only supported
 * change (see UserEditForm).
 */
export function UserCreateForm({ onSubmit, onCancel, submitLabel = "Create User" }: UserCreateFormProps) {
  const roleOptionsQuery = useRoleOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<UserCreateFormValues>({
    resolver: zodResolver(userCreateFormSchema),
    defaultValues: DEFAULT_USER_CREATE_FORM_VALUES,
  });

  async function handleFormSubmit(values: UserCreateFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<UserCreateFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  const roleOptions = (roleOptionsQuery.data ?? []).map((role) => ({
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

          <FormField
            label="Initial Password"
            required
            error={errors.password?.message}
            description="The account must change this password on first login."
          >
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                type="password"
                autoComplete="new-password"
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("password")}
              />
            )}
          </FormField>

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
            {isSubmitting ? "Creating…" : submitLabel}
          </Button>
        }
      />
    </form>
  );
}
