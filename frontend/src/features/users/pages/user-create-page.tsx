"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { UserCreateForm } from "@/features/users/components/user-create-form";
import { useCreateUser } from "@/features/users/hooks/use-create-user";
import { toUserCreateRequestPayload, type UserCreateFormValues } from "@/features/users/schemas/user-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

const USER_MANAGE_PERMISSION = "user:manage";

export function UserCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createUser = useCreateUser();

  if (!hasPermission(USER_MANAGE_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to create users"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: UserCreateFormValues) {
    const loadingToastId = toastLoading("Creating user…");
    try {
      const user = await createUser.mutateAsync(toUserCreateRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess(`${user.fullName} was created.`);
      router.push("/users");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is UserCreateForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="New User"
      description="Add an administrator or staff member and assign their role."
    >
      <UserCreateForm onSubmit={handleSubmit} onCancel={() => router.push("/users")} submitLabel="Create User" />
    </FormPageTemplate>
  );
}
