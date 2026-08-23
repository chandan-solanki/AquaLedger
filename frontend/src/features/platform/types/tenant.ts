/** Mirrors the backend's TenantStatus enum (app/modules/auth/constants.py). */
export type TenantStatus = "active" | "suspended" | "inactive";

/**
 * Raw backend shape (snake_case), matching TenantResponse
 * (app/modules/platform_admin/schemas.py) exactly. Deliberately excludes
 * `settings` (arbitrary JSONB, no use case yet) and any tenant business
 * data - id/name/slug/status/plan/currency/fiscal month plus timestamps
 * only, per the backend's own docstring.
 */
export interface BackendTenant {
  id: string;
  name: string;
  slug: string;
  status: TenantStatus;
  plan: string | null;
  base_currency: string;
  fiscal_year_start_month: number;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every platform tenant-service.ts function returns. */
export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: TenantStatus;
  plan: string | null;
  baseCurrency: string;
  fiscalYearStartMonth: number;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendTenant(tenant: BackendTenant): Tenant {
  return {
    id: tenant.id,
    name: tenant.name,
    slug: tenant.slug,
    status: tenant.status,
    plan: tenant.plan,
    baseCurrency: tenant.base_currency,
    fiscalYearStartMonth: tenant.fiscal_year_start_month,
    createdAt: tenant.created_at,
    updatedAt: tenant.updated_at,
  };
}

/** Never includes password/password_hash - returned once, at creation, so the platform admin can hand the initial admin their login email. */
export interface BackendTenantAdministratorSummary {
  id: string;
  email: string;
  username: string;
  full_name: string;
}

export interface TenantAdministratorSummary {
  id: string;
  email: string;
  username: string;
  fullName: string;
}

export interface BackendTenantProvisioningResponse {
  tenant: BackendTenant;
  administrator: BackendTenantAdministratorSummary;
}

export interface TenantProvisioningResult {
  tenant: Tenant;
  administrator: TenantAdministratorSummary;
}

export function mapBackendTenantProvisioningResponse(
  response: BackendTenantProvisioningResponse
): TenantProvisioningResult {
  return {
    tenant: mapBackendTenant(response.tenant),
    administrator: {
      id: response.administrator.id,
      email: response.administrator.email,
      username: response.administrator.username,
      fullName: response.administrator.full_name,
    },
  };
}

/**
 * Query params for GET /platform/tenants (TenantListParams,
 * app/modules/platform_admin/schemas.py) - snake_case to match the wire
 * format exactly, same convention as CompanyListParams. No `sort` field:
 * the backend endpoint has none (always newest-first).
 */
export interface TenantListParams {
  q?: string;
  status?: TenantStatus;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /platform/tenants (TenantCreateRequest,
 * app/modules/platform_admin/schemas.py). `plan`/`base_currency`/
 * `fiscal_year_start_month` are deliberately omitted here - the backend
 * defaults all three (null / "INR" / 4) and this session's provisioning UI
 * only collects what a platform admin actually needs to hand off a new
 * tenant: its identity and its first administrator. `extra="forbid"` on the
 * backend schema means nothing beyond these fields may ever be sent.
 */
export interface TenantCreateRequest {
  name: string;
  slug: string;
  administrator: {
    email: string;
    username: string;
    full_name: string;
    password: string;
  };
}

/** Request body for PATCH /platform/tenants/{id}/status (TenantStatusUpdateRequest). */
export interface TenantStatusUpdateRequest {
  status: TenantStatus;
}
