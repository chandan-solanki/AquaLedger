"use client";

import { Ban, Building2, CircleCheck, Landmark, Plus, PowerOff, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { DashboardMiniTable } from "@/components/dashboard";
import { MetricCard } from "@/components/data-display/metric-card";
import { SummaryGrid } from "@/components/data-display/summary-grid";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TENANT_STATUS_BADGE_VARIANT, TENANT_STATUS_LABELS } from "@/features/platform/constants/tenant-status";
import { usePlatformDashboard } from "@/features/platform/hooks/use-platform-dashboard";
import type { Tenant } from "@/features/platform/types/tenant";
import { normalizeApiError } from "@/utils/api-error";
import { formatDate } from "@/utils/format-date";
import { cn } from "@/lib/utils";

/**
 * The platform administrator's landing page (Sprint 17 Session 5) — a
 * tenant-lifecycle overview built entirely from GET /platform/dashboard,
 * never a duplicate of PlatformTenantListPage's own filtering/pagination.
 * Exists because the ordinary tenant `/dashboard` is intentionally
 * inaccessible to a platform admin (no `dashboard:view` or any other tenant
 * permission — Sprint 17 Session 1's boundary is never relaxed to make this
 * page work); this is a separate, platform-scoped page, not an RBAC bypass.
 */
export function PlatformDashboardPage() {
  const router = useRouter();
  const query = usePlatformDashboard();
  const apiError = query.isError ? normalizeApiError(query.error) : null;
  const data = query.data;

  if (apiError && !data) {
    return (
      <PageContainer>
        <ErrorState
          title="Failed to load the platform dashboard"
          description={apiError.message}
          onRetry={() => query.refetch()}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Platform Administration — Dashboard"
        description="Overview of tenants and platform lifecycle status."
        icon={Landmark}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Refresh platform dashboard"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw
                className={cn("size-4", query.isFetching && "animate-spin motion-reduce:animate-none")}
                aria-hidden
              />
            </Button>
            <Button asChild size="sm">
              <Link href="/platform/tenants/new">
                <Plus aria-hidden />
                New Tenant
              </Link>
            </Button>
          </div>
        }
      />

      {apiError && data && (
        <ErrorState
          variant="inline"
          title="Couldn't refresh the platform dashboard"
          description={`Showing the last-loaded data. ${apiError.message}`}
          onRetry={() => query.refetch()}
        />
      )}

      <SummaryGrid columns={4}>
        <MetricCard
          title="Total Tenants"
          value={String(data?.totalTenants ?? 0)}
          icon={Building2}
          isLoading={query.isLoading}
        />
        <MetricCard
          title="Active"
          value={String(data?.activeTenants ?? 0)}
          icon={CircleCheck}
          isLoading={query.isLoading}
        />
        <MetricCard
          title="Suspended"
          value={String(data?.suspendedTenants ?? 0)}
          icon={Ban}
          isLoading={query.isLoading}
        />
        <MetricCard
          title="Inactive"
          value={String(data?.inactiveTenants ?? 0)}
          icon={PowerOff}
          isLoading={query.isLoading}
        />
      </SummaryGrid>

      <DashboardMiniTable<Tenant>
        title="Recent Tenants"
        columns={[
          { key: "name", header: "Tenant Name", render: (tenant) => tenant.name },
          { key: "slug", header: "Slug", render: (tenant) => tenant.slug },
          {
            key: "status",
            header: "Status",
            render: (tenant) => (
              <Badge variant={TENANT_STATUS_BADGE_VARIANT[tenant.status]}>
                {TENANT_STATUS_LABELS[tenant.status]}
              </Badge>
            ),
          },
          {
            key: "createdAt",
            header: "Created At",
            align: "right",
            render: (tenant) => formatDate(tenant.createdAt),
          },
        ]}
        rows={data?.recentTenants ?? []}
        rowKey={(tenant) => tenant.id}
        onRowClick={(tenant) => router.push(`/platform/tenants/${tenant.id}`)}
        isLoading={query.isLoading}
        emptyIcon={Landmark}
        emptyMessage="No tenants yet."
      />

      <div className="flex justify-end">
        <Button asChild variant="outline">
          <Link href="/platform/tenants">View All Tenants</Link>
        </Button>
      </div>
    </PageContainer>
  );
}
