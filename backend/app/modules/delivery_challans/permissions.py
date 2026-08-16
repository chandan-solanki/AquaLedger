# Permission codes for the delivery_challans module, per ARCHITECTURE.md
# §9.2's resource:action convention and purchase_orders' own permissions.py
# shape. Lifecycle transitions (dispatch/deliver/cancel) each get their own
# code, mirroring purchase_order:confirm/cancel/fulfill - a transition is a
# distinct, separately-grantable capability from plain view/create/edit/delete.
DELIVERY_CHALLAN_VIEW = "delivery_challan:view"
DELIVERY_CHALLAN_CREATE = "delivery_challan:create"
DELIVERY_CHALLAN_EDIT = "delivery_challan:edit"
DELIVERY_CHALLAN_DELETE = "delivery_challan:delete"
DELIVERY_CHALLAN_DISPATCH = "delivery_challan:dispatch"
DELIVERY_CHALLAN_DELIVER = "delivery_challan:deliver"
DELIVERY_CHALLAN_CANCEL = "delivery_challan:cancel"
