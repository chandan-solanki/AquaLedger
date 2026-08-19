import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  AuditLogEntry,
  AuditLogListParams,
  BackendAuditLogEntry,
} from "@/features/audit-logs/types/audit-log";
import { mapBackendAuditLogEntry } from "@/features/audit-logs/types/audit-log";

export interface AuditLogListResult {
  data: AuditLogEntry[];
  meta: ApiListEnvelope<BackendAuditLogEntry>["meta"];
}

function buildQueryString(params: AuditLogListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.action) query.set("action", params.action);
  if (params.entity_type) query.set("entity_type", params.entity_type);
  if (params.user_id) query.set("user_id", params.user_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/audit-logs`) - never
 * the FastAPI backend directly, mirroring `document-service.ts`. Read-only:
 * this is the entire surface - no create/update/delete method exists here,
 * matching the backend's own audit_logs router (append-only history).
 */
export const auditLogService = {
  async listAuditLogs(params: AuditLogListParams): Promise<AuditLogListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendAuditLogEntry>>(
      `/audit-logs?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendAuditLogEntry), meta: data.meta };
  },
};
