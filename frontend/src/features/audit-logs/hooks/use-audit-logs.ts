"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { auditLogKeys } from "@/features/audit-logs/constants/query-keys";
import type { AuditLogFilters } from "@/features/audit-logs/schemas/audit-log-filters";
import { toAuditLogListParams } from "@/features/audit-logs/schemas/audit-log-filters";
import { auditLogService } from "@/features/audit-logs/services/audit-log-service";

/**
 * Server-side, paginated audit log list - every filter/sort/page change
 * refetches from the backend rather than filtering an already-loaded page
 * client-side, mirroring `useDocuments`.
 */
export function useAuditLogs(filters: AuditLogFilters) {
  const params = toAuditLogListParams(filters);

  return useQuery({
    queryKey: auditLogKeys.list(params),
    queryFn: () => auditLogService.listAuditLogs(params),
    placeholderData: keepPreviousData,
  });
}
