import type { AuditLogListParams } from "@/features/audit-logs/types/audit-log";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/audit_logs/schemas.py) - created_at only. */
export const AUDIT_LOG_SORT_FIELDS = ["created_at"] as const;
export type AuditLogSortField = (typeof AUDIT_LOG_SORT_FIELDS)[number];

export const AUDIT_LOG_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type AuditLogSortDirection = (typeof AUDIT_LOG_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `DocumentFilters` - `toAuditLogListParams` recombines them into
 * the wire format the backend actually expects.
 */
export interface AuditLogFilters {
  search: string;
  action: string | null;
  entityType: string | null;
  userId: string | null;
  fromDate: string | null;
  toDate: string | null;
  page: number;
  pageSize: number;
  sort: AuditLogSortField;
  direction: AuditLogSortDirection;
}

export const DEFAULT_AUDIT_LOG_FILTERS: AuditLogFilters = {
  search: "",
  action: null,
  entityType: null,
  userId: null,
  fromDate: null,
  toDate: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's AuditLogListParams query shape. */
export function toAuditLogListParams(filters: AuditLogFilters): AuditLogListParams {
  return {
    q: filters.search.trim() || undefined,
    action: filters.action ?? undefined,
    entity_type: filters.entityType ?? undefined,
    user_id: filters.userId ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
