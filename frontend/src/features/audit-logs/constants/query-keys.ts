import type { AuditLogListParams } from "@/features/audit-logs/types/audit-log";

/** Read-only, list-only feature (no detail endpoint - see the backend
 * router's module docstring) so unlike `userKeys` there is no
 * `details`/`detail` key. Mirrors `documentKeys` exactly. */
export const auditLogKeys = {
  all: () => ["audit-logs"] as const,
  lists: () => [...auditLogKeys.all(), "list"] as const,
  list: (params: AuditLogListParams) => [...auditLogKeys.lists(), params] as const,
};
