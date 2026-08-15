# Permission code for the reports module, per ARCHITECTURE.md §9.2.
# The reports module is read-only (TASKS.md Sprint 11 Session 1) and has
# exactly one permission - the same "single view permission, no CRUD
# surface" shape dashboard:view established for the last read-only module
# (app/modules/dashboard/permissions.py).
REPORTS_VIEW = "reports:view"
