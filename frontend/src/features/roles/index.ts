export { RoleListPage } from "@/features/roles/pages/role-list-page";
export { RoleDetailPage } from "@/features/roles/pages/role-detail-page";

export { RolePermissionMatrix, type RolePermissionMatrixProps } from "@/features/roles/components/role-permission-matrix";
export { getRoleColumns } from "@/features/roles/components/role-columns";

export { useRoles } from "@/features/roles/hooks/use-roles";
export { useRole } from "@/features/roles/hooks/use-role";
export { usePermissionsCatalog } from "@/features/roles/hooks/use-permissions-catalog";

export { roleService } from "@/features/roles/services/role-service";

export type {
  BackendRoleDetail,
  BackendRoleListItem,
  BackendRoleUserSummary,
  PermissionSummary,
  RoleDetail,
  RoleListItem,
  RoleUserSummary,
} from "@/features/roles/types/role";
export { mapBackendRoleDetail, mapBackendRoleListItem } from "@/features/roles/types/role";

export { roleKeys } from "@/features/roles/constants/query-keys";
