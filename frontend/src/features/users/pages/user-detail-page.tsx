"use client";

import { Ban, CircleCheck, Pencil, Users as UsersIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { SectionHeader } from "@/components/layout/section-header";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { USER_STATUS_BADGE_VARIANT, USER_STATUS_LABELS } from "@/features/users/constants/user-status";
import { useUpdateUserStatus } from "@/features/users/hooks/use-update-user-status";
import { useUser } from "@/features/users/hooks/use-user";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";

const USER_MANAGE_PERMISSION = "user:manage";

/**
 * Read-only User record view (identity + role + status), with
 * Activate/Deactivate as the one supported mutation from this page - editing
 * identity/role fields goes through the Edit page, and there is no
 * admin-triggered password reset (see UserUpdateRequest's doc comment).
 */
export function UserDetailPage() {
  const params = useParams<{ id: string }>();
  const userId = params.id;
  const { hasPermission } = usePermissions();
  const currentUser = useCurrentUser();
  const [isStatusDialogOpen, setIsStatusDialogOpen] = useState(false);

  const userQuery = useUser(userId);
  const updateUserStatus = useUpdateUserStatus();

  if (!hasPermission(USER_MANAGE_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to view users"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const user = userQuery.data;
  const apiError = userQuery.isError ? normalizeApiError(userQuery.error) : null;
  const isDeactivating = user?.status !== "inactive";
  const nextStatus = isDeactivating ? "inactive" : "active";
  const isSelf = user?.id === currentUser?.id;

  return (
    <DetailPageTemplate
      title={user?.fullName ?? "User"}
      description={user?.email}
      icon={UsersIcon}
      badge={
        user && <Badge variant={USER_STATUS_BADGE_VARIANT[user.status]}>{USER_STATUS_LABELS[user.status]}</Badge>
      }
      primaryAction={user ? { label: "Edit Role", icon: Pencil, href: `/users/${user.id}/edit` } : undefined}
      secondaryActions={
        user
          ? [
              {
                label: isDeactivating ? "Deactivate" : "Activate",
                icon: isDeactivating ? Ban : CircleCheck,
                onClick: () => setIsStatusDialogOpen(true),
                disabled: isDeactivating && isSelf,
              },
            ]
          : undefined
      }
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
      {user && (
        <div className="space-y-6">
          <SectionHeader title="User Information" />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <InfoCard title="Details">
              <DescriptionList
                items={[
                  { term: "Full Name", details: user.fullName },
                  { term: "Email", details: user.email },
                  { term: "Username", details: user.username },
                  { term: "Phone", details: user.phone ?? "—" },
                  { term: "Role", details: user.role?.name ?? "—" },
                  { term: "Status", details: USER_STATUS_LABELS[user.status] },
                  { term: "Superuser", details: user.isSuperuser ? "Yes" : "No" },
                ]}
              />
            </InfoCard>

            <InfoCard title="Activity">
              <DescriptionList
                items={[
                  { term: "Last Active", details: user.lastLoginAt ? formatDateTime(user.lastLoginAt) : "Never" },
                  { term: "Created At", details: formatDateTime(user.createdAt) },
                  { term: "Updated At", details: formatDateTime(user.updatedAt) },
                ]}
              />
            </InfoCard>
          </div>
        </div>
      )}

      {user && (
        <ConfirmationDialog
          open={isStatusDialogOpen}
          onOpenChange={setIsStatusDialogOpen}
          title={isDeactivating ? `Deactivate ${user.fullName}?` : `Activate ${user.fullName}?`}
          description={
            isDeactivating
              ? "They will be signed out everywhere and unable to log in until reactivated."
              : "They will be able to log in again."
          }
          variant={isDeactivating ? "destructive" : "default"}
          confirmLabel={isDeactivating ? "Deactivate" : "Activate"}
          isLoading={updateUserStatus.isPending}
          onConfirm={() =>
            updateUserStatus.mutate(
              { id: user.id, status: nextStatus },
              { onSuccess: () => setIsStatusDialogOpen(false) }
            )
          }
        />
      )}
    </DetailPageTemplate>
  );
}
