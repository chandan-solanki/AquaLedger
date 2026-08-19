/** Mirrors the backend's AuditLogActor (app/modules/audit_logs/schemas.py) -
 * never carries a password or password_hash field. */
export interface BackendAuditLogActor {
  id: string;
  full_name: string;
  email: string;
}

/**
 * Raw backend shape (snake_case), matching AuditLogListItem
 * (app/modules/audit_logs/schemas.py) exactly. `actor` is null for records
 * with no associated user (AuditLog.user_id is nullable - e.g. a failed
 * login against an unknown email).
 */
export interface BackendAuditLogEntry {
  id: string;
  tenant_id: string;
  actor: BackendAuditLogActor | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

/** The client-facing, camelCase shape every audit-log-service.ts function returns. */
export interface AuditLogEntry {
  id: string;
  tenantId: string;
  actor: { id: string; fullName: string; email: string } | null;
  action: string;
  entityType: string;
  entityId: string | null;
  changes: Record<string, unknown> | null;
  ipAddress: string | null;
  userAgent: string | null;
  createdAt: string;
}

export function mapBackendAuditLogEntry(entry: BackendAuditLogEntry): AuditLogEntry {
  return {
    id: entry.id,
    tenantId: entry.tenant_id,
    actor: entry.actor
      ? { id: entry.actor.id, fullName: entry.actor.full_name, email: entry.actor.email }
      : null,
    action: entry.action,
    entityType: entry.entity_type,
    entityId: entry.entity_id,
    changes: entry.changes,
    ipAddress: entry.ip_address,
    userAgent: entry.user_agent,
    createdAt: entry.created_at,
  };
}

/** Query params for GET /audit-logs (app/modules/audit_logs/schemas.py's AuditLogListParams). */
export interface AuditLogListParams {
  q?: string;
  action?: string;
  entity_type?: string;
  user_id?: string;
  from_date?: string;
  to_date?: string;
  sort: string;
  page: number;
  page_size: number;
}
