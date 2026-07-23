# Permission codes for the payments module, per ARCHITECTURE.md §9.2.
#
# payment:view and payment:delete were already seeded in the baseline
# migration (67c33121fc54) alongside every other module's roadmap-wide RBAC
# surface, before this module existed - the same situation invoice:view/
# create/edit/issue found themselves in ahead of the invoices module
# (see invoices/permissions.py). Both are reused as-is here.
#
# payment:record and payment:bounce also exist in that same baseline seed,
# for the allocate-on-record and cheque-bounce workflows ARCHITECTURE.md
# §14.1/§14.4 originally sketched. This sprint's as-built design (TASKS.md)
# instead models payments as an explicit Draft -> Posted -> Cancelled state
# machine, the same as-built deviation Invoice made from ARCHITECTURE's
# invoice_type/parent_invoice_id - so payment:record/bounce stay unused for
# now, the same way invoice:cancel sits unused pending a future credit-note
# sprint.
#
# payment:create, payment:edit and payment:post are the gap this sprint
# fills - seeded in this sprint's own migration, the same pattern
# a1c9f7e3d5b2 used to add invoice:delete on top of the baseline set.
# payment:post guards the future Session 5 state-transition endpoint
# (POST /payments/{id}/post), the same route-level-permission pattern
# invoice:issue uses for invoices.
PAYMENT_VIEW = "payment:view"
PAYMENT_CREATE = "payment:create"
PAYMENT_EDIT = "payment:edit"
PAYMENT_DELETE = "payment:delete"
PAYMENT_POST = "payment:post"
