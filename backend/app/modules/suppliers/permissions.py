# Permission codes for the suppliers module, per ARCHITECTURE.md §9.2's
# resource:action convention and TASKS.md Sprint 11 Session 1's requested
# surface. Unlike payment:view/delete or invoice:view/create (which existed
# in the baseline migration ahead of their modules), no supplier/purchase
# permission was part of the original roadmap-wide baseline seed - this
# sprint introduces the entire surface fresh, in its own migration.
SUPPLIER_VIEW = "supplier:view"
SUPPLIER_CREATE = "supplier:create"
SUPPLIER_EDIT = "supplier:edit"
SUPPLIER_DELETE = "supplier:delete"
