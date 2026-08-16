# Permission codes for the purchase_orders module, per ARCHITECTURE.md
# §9.2's resource:action convention and the purchase module's own
# purchase:* surface. Lifecycle transitions (confirm/cancel/fulfill) each
# get their own code, mirroring purchase:post - a transition is a distinct,
# separately-grantable capability from plain view/create/edit/delete.
PURCHASE_ORDER_VIEW = "purchase_order:view"
PURCHASE_ORDER_CREATE = "purchase_order:create"
PURCHASE_ORDER_EDIT = "purchase_order:edit"
PURCHASE_ORDER_DELETE = "purchase_order:delete"
PURCHASE_ORDER_CONFIRM = "purchase_order:confirm"
PURCHASE_ORDER_CANCEL = "purchase_order:cancel"
PURCHASE_ORDER_FULFILL = "purchase_order:fulfill"
