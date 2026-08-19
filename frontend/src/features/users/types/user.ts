/** Mirrors the backend's AccountStatus enum (app/modules/auth/constants.py). */
export type UserAccountStatus = "active" | "inactive" | "locked" | "password_expired";

/** The only two values an administrator can set via PATCH /users/{id}/status -
 * locked/password_expired are system-managed (AuthService), never admin-set. */
export type UserStatusAction = "active" | "inactive";

/** Mirrors the backend's RoleSummary (app/modules/users/schemas.py). */
export interface RoleSummary {
  id: string;
  name: string;
  description: string | null;
}

/**
 * Raw backend shape (snake_case), matching UserResponse
 * (app/modules/users/schemas.py) exactly. Never carries a password or
 * password_hash field - the backend never returns one.
 */
export interface BackendUser {
  id: string;
  tenant_id: string;
  email: string;
  username: string;
  full_name: string;
  phone: string | null;
  status: UserAccountStatus;
  is_superuser: boolean;
  last_login_at: string | null;
  role: RoleSummary | null;
  created_at: string;
  updated_at: string;
}

/**
 * The client-facing, camelCase shape every user-service.ts function returns.
 * Named `ManagedUser` (not `User`) to stay distinct from
 * `@/features/auth/types/auth`'s `User` - the currently-authenticated
 * session user - since pages here need both at once (the acting admin and
 * the user record being administered).
 */
export interface ManagedUser {
  id: string;
  tenantId: string;
  email: string;
  username: string;
  fullName: string;
  phone: string | null;
  status: UserAccountStatus;
  isSuperuser: boolean;
  lastLoginAt: string | null;
  role: RoleSummary | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendUser(user: BackendUser): ManagedUser {
  return {
    id: user.id,
    tenantId: user.tenant_id,
    email: user.email,
    username: user.username,
    fullName: user.full_name,
    phone: user.phone,
    status: user.status,
    isSuperuser: user.is_superuser,
    lastLoginAt: user.last_login_at,
    role: user.role,
    createdAt: user.created_at,
    updatedAt: user.updated_at,
  };
}

/** Query params for GET /users (app/modules/users/schemas.py's UserListParams). */
export interface UserListParams {
  q?: string;
  role_id?: string;
  status?: UserAccountStatus;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /users (UserCreateRequest). No `is_superuser`
 * field at all - the backend never accepts one through this endpoint.
 */
export interface UserCreateRequest {
  email: string;
  username: string;
  full_name: string;
  phone?: string;
  password: string;
  role_id: string;
}

/** Request body for PUT /users/{id} (UserUpdateRequest) - a partial update, only present fields change. No password field - see UserCreateRequest's note. */
export interface UserUpdateRequest {
  email?: string;
  username?: string;
  full_name?: string;
  phone?: string;
  role_id?: string;
}

/** Request body for PATCH /users/{id}/status. */
export interface UserStatusUpdateRequest {
  status: UserStatusAction;
}
