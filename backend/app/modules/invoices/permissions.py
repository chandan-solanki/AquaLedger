# Permission codes for the invoices module, per ARCHITECTURE.md §9.2.
# invoice:view/create/edit/issue were seeded upfront in the baseline
# migration (67c33121fc54) along with the rest of the roadmap's RBAC
# surface, before this module existed. invoice:delete was the one gap -
# added in migration a1c9f7e3d5b2, the same way trip:delete (244f758929a6)
# filled the equivalent gap for trips.
#
# invoice:issue guards the Session 5 state-transition endpoint
# (POST /invoices/{id}/issue) as its own route-level permission, the same
# pattern trip:close uses for trips - a state transition is a distinct
# action with its own preconditions, not covered by invoice:edit (issued
# invoices are immutable and can never be reached through the edit path).
#
# invoice:cancel also already exists in the baseline seed for the future
# cancel/credit-note workflow, but that's out of scope for this sprint's
# six sessions (see models.py's Invoice docstring), so it has no constant
# here yet.
INVOICE_VIEW = "invoice:view"
INVOICE_CREATE = "invoice:create"
INVOICE_EDIT = "invoice:edit"
INVOICE_DELETE = "invoice:delete"
INVOICE_ISSUE = "invoice:issue"
