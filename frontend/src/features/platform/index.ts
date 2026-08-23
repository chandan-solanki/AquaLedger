export { PlatformDashboardPage } from "@/features/platform/pages/platform-dashboard-page";
export { PlatformTenantListPage } from "@/features/platform/pages/platform-tenant-list-page";
export { PlatformTenantCreatePage } from "@/features/platform/pages/platform-tenant-create-page";
export { PlatformTenantDetailPage } from "@/features/platform/pages/platform-tenant-detail-page";

export { PlatformGuard } from "@/features/platform/components/platform-guard";
export { TenantForm, type TenantFormProps } from "@/features/platform/components/tenant-form";
export { getTenantColumns } from "@/features/platform/components/tenant-columns";

export { useTenants } from "@/features/platform/hooks/use-tenants";
export { useTenant } from "@/features/platform/hooks/use-tenant";
export { useTenantFilters } from "@/features/platform/hooks/use-tenant-filters";
export { useCreateTenant } from "@/features/platform/hooks/use-create-tenant";
export {
  useUpdateTenantStatus,
  type UpdateTenantStatusVariables,
} from "@/features/platform/hooks/use-update-tenant-status";

export { platformTenantService } from "@/features/platform/services/tenant-service";
export type { TenantListResult } from "@/features/platform/services/tenant-service";

export type {
  BackendTenant,
  BackendTenantAdministratorSummary,
  BackendTenantProvisioningResponse,
  Tenant,
  TenantAdministratorSummary,
  TenantCreateRequest,
  TenantListParams,
  TenantProvisioningResult,
  TenantStatus,
  TenantStatusUpdateRequest,
} from "@/features/platform/types/tenant";
export { mapBackendTenant, mapBackendTenantProvisioningResponse } from "@/features/platform/types/tenant";

export type { TenantFilters } from "@/features/platform/schemas/tenant-filters";
export { DEFAULT_TENANT_FILTERS, toTenantListParams } from "@/features/platform/schemas/tenant-filters";

export type { TenantFormValues } from "@/features/platform/schemas/tenant-form-schema";
export {
  DEFAULT_TENANT_FORM_VALUES,
  tenantFormSchema,
  toTenantCreateRequestPayload,
} from "@/features/platform/schemas/tenant-form-schema";

export {
  TENANT_STATUS_BADGE_VARIANT,
  TENANT_STATUS_LABELS,
  TENANT_STATUS_OPTIONS,
  TENANT_STATUS_VALUES,
} from "@/features/platform/constants/tenant-status";

export { platformDashboardKeys, platformTenantKeys } from "@/features/platform/constants/query-keys";

export { usePlatformDashboard } from "@/features/platform/hooks/use-platform-dashboard";
export { platformDashboardService } from "@/features/platform/services/platform-dashboard-service";
export type {
  BackendPlatformDashboard,
  PlatformDashboardData,
} from "@/features/platform/types/platform-dashboard";
export { mapBackendPlatformDashboard } from "@/features/platform/types/platform-dashboard";
