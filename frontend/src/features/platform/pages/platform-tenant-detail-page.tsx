"use client";

import { Ban, CircleCheck, KeyRound, Landmark, PowerOff } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { SectionHeader } from "@/components/layout/section-header";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TENANT_STATUS_BADGE_VARIANT, TENANT_STATUS_LABELS } from "@/features/platform/constants/tenant-status";
import { useResetTenantAdministratorPassword } from "@/features/platform/hooks/use-reset-tenant-administrator-password";
import { useTenant } from "@/features/platform/hooks/use-tenant";
import { useTenantAdministrators } from "@/features/platform/hooks/use-tenant-administrators";
import { useUpdateTenantStatus } from "@/features/platform/hooks/use-update-tenant-status";
import type { TenantAdministrator } from "@/features/platform/types/tenant-administrator";
import type { TenantStatus } from "@/features/platform/types/tenant";
import { ResetPasswordDialog } from "@/features/users/components/reset-password-dialog";
import { USER_STATUS_BADGE_VARIANT, USER_STATUS_LABELS } from "@/features/users/constants/user-status";
import type { UserPasswordResetFormValues } from "@/features/users/schemas/user-form-schema";
import { toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";

type PendingAction = { targetStatus: TenantStatus; label: string; description: string; variant: "default" | "destructive" } | null;

/**
 * Read-only tenant lifecycle view — identity, slug, status, and provisioning
 * timestamps only, exactly what GET /platform/tenants/{id} returns. No
 * initial-administrator info (the backend never returns it here — that
 * summary is a one-time provisioning response, not part of this resource),
 * and no cross-tenant business data of any kind (Sprint 17 Session 4 scope).
 *
 * Every direct status transition the backend actually supports is offered
 * here: from ACTIVE, Suspend or Deactivate (each a destructive,
 * confirmation-gated action); from SUSPENDED or INACTIVE, Reactivate.
 */
export function PlatformTenantDetailPage() {
  const params = useParams<{ id: string }>();
  const tenantId = params.id;
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [passwordResetTarget, setPasswordResetTarget] = useState<TenantAdministrator | null>(null);

  const tenantQuery = useTenant(tenantId);
  const updateTenantStatus = useUpdateTenantStatus();
  const administratorsQuery = useTenantAdministrators(tenantId);
  const resetAdministratorPassword = useResetTenantAdministratorPassword();

  const tenant = tenantQuery.data;
  const apiError = tenantQuery.isError ? normalizeApiError(tenantQuery.error) : null;
  const administrators = administratorsQuery.data ?? [];

  async function handleResetAdministratorPassword(values: UserPasswordResetFormValues) {
    if (!passwordResetTarget) return;
    await resetAdministratorPassword.mutateAsync({
      tenantId,
      userId: passwordResetTarget.id,
      newPassword: values.new_password,
    });
    toastSuccess(`${passwordResetTarget.fullName}'s password was reset.`);
    setPasswordResetTarget(null);
  }

  const secondaryActions = tenant
    ? tenant.status === "active"
      ? [
          {
            label: "Suspend",
            icon: Ban,
            onClick: () =>
              setPendingAction({
                targetStatus: "suspended",
                label: "Suspend",
                variant: "destructive",
                description:
                  "Every user in this tenant will be blocked immediately: existing access tokens are rejected on their next request, refresh tokens are revoked, and login is blocked until the tenant is reactivated.",
              }),
          },
          {
            label: "Deactivate",
            icon: PowerOff,
            onClick: () =>
              setPendingAction({
                targetStatus: "inactive",
                label: "Deactivate",
                variant: "destructive",
                description:
                  "Every user in this tenant will be blocked immediately: existing access tokens are rejected on their next request, refresh tokens are revoked, and login is blocked until the tenant is reactivated.",
              }),
          },
        ]
      : [
          {
            label: "Reactivate",
            icon: CircleCheck,
            onClick: () =>
              setPendingAction({
                targetStatus: "active",
                label: "Reactivate",
                variant: "default",
                description:
                  "Users in this tenant will be able to log in again. Their previous sessions were revoked while the tenant was not active, so they will need to sign in again.",
              }),
          },
        ]
    : undefined;

  return (
    <DetailPageTemplate
      title={tenant?.name ?? "Tenant"}
      description={tenant?.slug}
      icon={Landmark}
      badge={
        tenant && (
          <Badge variant={TENANT_STATUS_BADGE_VARIANT[tenant.status]}>
            {TENANT_STATUS_LABELS[tenant.status]}
          </Badge>
        )
      }
      secondaryActions={secondaryActions}
      isLoading={tenantQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load tenant",
              description: apiError.message,
              onRetry: () => tenantQuery.refetch(),
            }
          : null
      }
    >
      {tenant && (
        <div className="space-y-6">
          <SectionHeader title="Tenant Information" />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <InfoCard title="Details">
              <DescriptionList
                items={[
                  { term: "Tenant Name", details: tenant.name },
                  { term: "Slug", details: tenant.slug },
                  { term: "Status", details: TENANT_STATUS_LABELS[tenant.status] },
                  { term: "Plan", details: tenant.plan ?? "—" },
                ]}
              />
            </InfoCard>

            <InfoCard title="Configuration">
              <DescriptionList
                items={[
                  { term: "Base Currency", details: tenant.baseCurrency },
                  { term: "Fiscal Year Start Month", details: String(tenant.fiscalYearStartMonth) },
                  { term: "Created At", details: formatDateTime(tenant.createdAt) },
                  { term: "Updated At", details: formatDateTime(tenant.updatedAt) },
                ]}
              />
            </InfoCard>
          </div>

          <SectionHeader
            title="Administrators"
            description="Active users with administrator access to this tenant. Resetting a password immediately signs that user out everywhere and forces them to set a new one on next login."
          />

          <InfoCard>
            {administratorsQuery.isLoading ? (
              <div className="space-y-3" aria-hidden>
                {Array.from({ length: 2 }).map((_, index) => (
                  <Skeleton key={index} className="h-10 w-full" />
                ))}
              </div>
            ) : administrators.length === 0 ? (
              <EmptyState title="No active administrators" description="This tenant has no active administrator account." />
            ) : (
              <ul className="divide-y divide-border">
                {administrators.map((administrator) => (
                  <li
                    key={administrator.id}
                    className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-medium text-foreground">
                          {administrator.fullName}
                        </p>
                        <Badge variant={USER_STATUS_BADGE_VARIANT[administrator.status]}>
                          {USER_STATUS_LABELS[administrator.status]}
                        </Badge>
                      </div>
                      <p className="truncate text-sm text-muted-foreground">{administrator.email}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="shrink-0"
                      onClick={() => setPasswordResetTarget(administrator)}
                    >
                      <KeyRound aria-hidden />
                      Reset Password
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </InfoCard>
        </div>
      )}

      {passwordResetTarget && (
        <ResetPasswordDialog
          open={Boolean(passwordResetTarget)}
          onOpenChange={(open) => !open && setPasswordResetTarget(null)}
          userName={passwordResetTarget.fullName}
          onSubmit={handleResetAdministratorPassword}
        />
      )}

      {tenant && pendingAction && (
        <ConfirmationDialog
          open={Boolean(pendingAction)}
          onOpenChange={(open) => !open && setPendingAction(null)}
          title={`${pendingAction.label} ${tenant.name}?`}
          description={pendingAction.description}
          variant={pendingAction.variant}
          confirmLabel={pendingAction.label}
          isLoading={updateTenantStatus.isPending}
          onConfirm={() =>
            updateTenantStatus.mutate(
              { id: tenant.id, status: pendingAction.targetStatus },
              { onSuccess: () => setPendingAction(null) }
            )
          }
        />
      )}
    </DetailPageTemplate>
  );
}
