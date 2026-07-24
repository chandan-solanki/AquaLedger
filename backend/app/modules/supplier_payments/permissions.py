# Permission codes for the supplier_payments module, per ARCHITECTURE.md
# §9.2's resource:action convention and TASKS.md Sprint 12 Session 1's
# requested surface. No supplier_payment:* code existed before this sprint -
# this module introduces the entire surface fresh, seeded in this sprint's
# own migration (mirrors migration 578d0e205274's approach for supplier:*/
# purchase:*, rather than splitting a baseline subset from a later top-up).
SUPPLIER_PAYMENT_VIEW = "supplier_payment:view"
SUPPLIER_PAYMENT_CREATE = "supplier_payment:create"
SUPPLIER_PAYMENT_EDIT = "supplier_payment:edit"
SUPPLIER_PAYMENT_DELETE = "supplier_payment:delete"
SUPPLIER_PAYMENT_POST = "supplier_payment:post"
