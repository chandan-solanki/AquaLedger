"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { UserEditForm } from "@/features/users/components/user-edit-form";
import { useUpdateUser } from "@/features/users/hooks/use-update-user";
import { useUser } from "@/features/users/hooks/use-user";
import { toUserEditFormValues, toUserUpdatePayload, type UserEditFormValues } from "@/features/users/schemas/user-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

const USER_MANAGE_PERMISSION = "user:manage";

export function UserEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const userId = params.id;
  const { hasPermission } = usePermissions();

  const userQuery = useUser(userId);
  const updateUser = useUpdateUser();

  if (!hasPermission(USER_MANAGE_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to edit users"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = userQuery.isError ? normalizeApiError(userQuery.error) : null;

  async function handleSubmit(values: UserEditFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      const user = await updateUser.mutateAsync({ id: userId, payload: toUserUpdatePayload(values) });
      dismissToast(loadingToastId);
      toastSuccess(`${user.fullName} was updated.`);
      router.push("/users");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is UserEditForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit User"
      description={userQuery.data?.fullName}
      isLoading={userQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load user",
              description: apiError.message,
              onRetry: () => userQuery.refetch(),
            }
          : null
      }
    >
      {userQuery.data && (
        <UserEditForm
          defaultValues={toUserEditFormValues(userQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/users")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
