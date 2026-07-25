/**
 * Mirrors the backend's AccountStatus enum (app/modules/auth/constants.py).
 */
export type AccountStatus = "active" | "inactive" | "locked" | "password_expired";

/**
 * The client-facing user shape, as returned by the BFF (not the backend
 * directly). Reshaped from the backend's UserProfileResponse — camelCase,
 * with `permissions`/`roles` kept as the same code/name string arrays the
 * backend returns (07_FRONTEND_ARCHITECTURE.md §11: the frontend's RBAC
 * layer is a read-only reflection of the backend's resource:action model,
 * never re-derived from role names).
 */
export interface User {
  id: string;
  tenantId: string;
  email: string;
  username: string;
  fullName: string;
  phone: string | null;
  status: AccountStatus;
  isSuperuser: boolean;
  lastLoginAt: string | null;
  roles: string[];
  permissions: string[];
  mustChangePassword: boolean;
}

/**
 * Minimal tenant reference available at auth time (backend only returns
 * `tenant_id` from /auth/me — richer tenant data, if ever needed, comes
 * from the future tenant settings endpoint, Sprint 9).
 */
export interface Tenant {
  id: string;
}

/** A `resource:action` permission code, e.g. "invoice:issue". */
export type Permission = string;

/** A role name, e.g. "accountant". */
export type Role = string;

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe: boolean;
}

/** What the client sends to the BFF's /api/auth/login route. */
export type LoginRequest = LoginCredentials;

/** What the BFF's /api/auth/login route returns — tokens never leave the server. */
export interface LoginResponse {
  user: User;
}

export interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  permissions: Permission[];
  isAuthenticated: boolean;
  isLoading: boolean;
}

/**
 * Mirrors the backend's AccessTokenPayload (app/modules/auth/schemas.py).
 * The client never sees a real access token (HttpOnly-cookie only), so this
 * type exists for the BFF's own server-side use and as a documented
 * contract, not for client-side authorization decisions.
 */
export interface JwtPayload {
  sub: string;
  tenant_id: string;
  roles: string[];
  permissions: string[];
  jti: string;
  iat: number;
  exp: number;
}
