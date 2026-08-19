import type { UserAccountStatus, UserListParams } from "@/features/users/types/user";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/users/schemas.py) exactly. */
export const USER_SORT_FIELDS = ["full_name", "email", "username", "created_at", "last_login_at"] as const;
export type UserSortField = (typeof USER_SORT_FIELDS)[number];

export const USER_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type UserSortDirection = (typeof USER_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` kept separate (rather than the backend's combined
 * `-field` string) since each is its own URL search param, mirroring
 * CompanyFilters - `toUserListParams` recombines them into the wire format.
 */
export interface UserFilters {
  search: string;
  roleId: string | null;
  status: UserAccountStatus | null;
  page: number;
  pageSize: number;
  sort: UserSortField;
  direction: UserSortDirection;
}

export const DEFAULT_USER_FILTERS: UserFilters = {
  search: "",
  roleId: null,
  status: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's UserListParams query shape. */
export function toUserListParams(filters: UserFilters): UserListParams {
  return {
    q: filters.search.trim() || undefined,
    role_id: filters.roleId ?? undefined,
    status: filters.status ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
