"use client";

import { Ban, CircleCheck, Landmark, PowerOff } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { SectionHeader } from "@/components/layout/section-header";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { TENANT_STATUS_BADGE_VARIANT, TENANT_STATUS_LABELS } from "@/features/platform/constants/tenant-status";
import { useTenant } from "@/features/platform/hooks/use-tenant";
import { useUpdateTenantStatus } from "@/features/platform/hooks/use-update-tenant-status";
import type { TenantStatus } from "@/features/platform/types/tenant";
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

  const tenantQuery = useTenant(tenantId);
  const updateTenantStatus = useUpdateTenantStatus();

  const tenant = tenantQuery.data;
  const apiError = tenantQuery.isError ? normalizeApiError(tenantQuery.error) : null;

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
        </div>
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
