import type { UserAccountStatus } from "@/features/users/types/user";

/** Mirrors the backend's PermissionSummary (app/modules/roles/schemas.py).
 * Global reference data - the same set regardless of tenant, so there's no
 * snake_case/camelCase mapping needed (every field is already a single word). */
export interface PermissionSummary {
  id: string;
  code: string;
  resource: string;
  action: string;
  description: string | null;
}

export interface BackendRoleUserSummary {
  id: string;
  full_name: string;
  email: string;
  status: UserAccountStatus;
}

export interface RoleUserSummary {
  id: string;
  fullName: string;
  email: string;
  status: UserAccountStatus;
}

function mapRoleUser(user: BackendRoleUserSummary): RoleUserSummary {
  return { id: user.id, fullName: user.full_name, email: user.email, status: user.status };
}

/** Raw backend shape (snake_case), matching RoleListItem (app/modules/roles/schemas.py). */
export interface BackendRoleListItem {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  user_count: number;
  permission_count: number;
  created_at: string;
  updated_at: string;
}

export interface RoleListItem {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  isSystem: boolean;
  userCount: number;
  permissionCount: number;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendRoleListItem(role: BackendRoleListItem): RoleListItem {
  return {
    id: role.id,
    tenantId: role.tenant_id,
    name: role.name,
    description: role.description,
    isSystem: role.is_system,
    userCount: role.user_count,
    permissionCount: role.permission_count,
    createdAt: role.created_at,
    updatedAt: role.updated_at,
  };
}

/** Raw backend shape, matching RoleDetailResponse - read-only (no
 * corresponding update payload type exists; see role-service.ts). */
export interface BackendRoleDetail {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: PermissionSummary[];
  users: BackendRoleUserSummary[];
  created_at: string;
  updated_at: string;
}

export interface RoleDetail {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  isSystem: boolean;
  permissions: PermissionSummary[];
  users: RoleUserSummary[];
  createdAt: string;
  updatedAt: string;
}

export function mapBackendRoleDetail(role: BackendRoleDetail): RoleDetail {
  return {
    id: role.id,
    tenantId: role.tenant_id,
    name: role.name,
    description: role.description,
    isSystem: role.is_system,
    permissions: role.permissions,
    users: role.users.map(mapRoleUser),
    createdAt: role.created_at,
    updatedAt: role.updated_at,
  };
}
