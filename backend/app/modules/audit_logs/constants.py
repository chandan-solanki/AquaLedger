# Reuses the "audit_log:view" permission seeded by the baseline auth
# migration (67c33121fc54) - it already exists for exactly this purpose
# (granted to super_admin/admin/manager, not accountant/operator) and
# already gates the Administration -> Audit Logs nav entry (frontend
# navigation.ts). No new permission code was needed, and user:manage is
# deliberately not reused here - the architecture already distinguishes
# audit access from user administration.
AUDIT_LOG_VIEW_PERMISSION = "audit_log:view"
