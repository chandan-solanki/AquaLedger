# Permission code for the dashboard module, per ARCHITECTURE.md §9.2.
# Seeded in migration <dashboard_permission> (Sprint 10 Session 1) - the
# dashboard is read-only, so this is the module's only permission code
# (contrast with trips/invoices/purchase which each have view/create/edit/...).
DASHBOARD_VIEW = "dashboard:view"
