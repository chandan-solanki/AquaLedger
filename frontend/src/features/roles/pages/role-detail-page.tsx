"use client";

import { KeyRound } from "lucide-react";
import { useParams } from "next/navigation";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SectionHeader } from "@/components/layout/section-header";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { RolePermissionMatrix } from "@/features/roles/components/role-permission-matrix";
import { useRole } from "@/features/roles/hooks/use-role";
import { usePermissionsCatalog } from "@/features/roles/hooks/use-permissions-catalog";
import { USER_STATUS_BADGE_VARIANT, USER_STATUS_LABELS } from "@/features/users/constants/user-status";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";

const USER_MANAGE_PERMISSION = "user:manage";

/**
 * Read-only Role record view: overview, current members, and a grouped
 * permission checklist. No Edit action - permission assignment isn't
 * supported by this module yet (app/modules/roles/router.py's module
 * docstring explains why); the note below the Permissions heading tells the
 * viewing admin the same thing, so the disabled checkboxes don't read as a
 * bug.
 */
export function RoleDetailPage() {
  const params = useParams<{ id: string }>();
  const roleId = params.id;
  const { hasPermission } = usePermissions();

  const roleQuery = useRole(roleId);
  const permissionsCatalogQuery = usePermissionsCatalog();

  if (!hasPermission(USER_MANAGE_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to view roles"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const role = roleQuery.data;
  const apiError = roleQuery.isError ? normalizeApiError(roleQuery.error) : null;
  const isLoading = roleQuery.isLoading || permissionsCatalogQuery.isLoading;

  return (
    <DetailPageTemplate
      title={role?.name ?? "Role"}
      description={role?.description ?? undefined}
      icon={KeyRound}
      badge={role?.isSystem && <Badge variant="outline">System Role</Badge>}
      isLoading={isLoading}
      error={
        apiError
          ? {
              title: "Failed to load role",
              description: apiError.message,
              onRetry: () => roleQuery.refetch(),
            }
          : null
      }
    >
      {role && (
        <div className="space-y-6">
          <SectionHeader title="Role Information" />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <InfoCard title="Details">
              <DescriptionList
                items={[
                  { term: "Name", details: role.name },
                  { term: "Description", details: role.description ?? "—" },
                  { term: "Type", details: role.isSystem ? "System role" : "Custom role" },
                  { term: "Permissions Granted", details: role.permissions.length },
                  { term: "Users", details: role.users.length },
                  { term: "Created At", details: formatDateTime(role.createdAt) },
                  { term: "Updated At", details: formatDateTime(role.updatedAt) },
                ]}
              />
            </InfoCard>

            <InfoCard title="Members">
              {role.users.length > 0 ? (
                <ul className="divide-y divide-border">
                  {role.users.map((user) => (
                    <li key={user.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-foreground">{user.fullName}</p>
                        <p className="truncate text-sm text-muted-foreground">{user.email}</p>
                      </div>
                      <Badge variant={USER_STATUS_BADGE_VARIANT[user.status]} className="shrink-0">
                        {USER_STATUS_LABELS[user.status]}
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="No users hold this role" description="Users assigned this role will appear here." />
              )}
            </InfoCard>
          </div>

          <div className="space-y-2">
            <SectionHeader
              title="Permissions"
              description="Read-only for now - permission assignment isn't available in this release."
            />
            {permissionsCatalogQuery.data && (
              <RolePermissionMatrix
                allPermissions={permissionsCatalogQuery.data}
                assignedCodes={new Set(role.permissions.map((p) => p.code))}
              />
            )}
          </div>
        </div>
      )}
    </DetailPageTemplate>
  );
}
