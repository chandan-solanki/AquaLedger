"use client";

import { Ban, CheckCircle2, ClipboardList, Pencil, PackageCheck, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { MetricCard } from "@/components/data-display/metric-card";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { ContentSection } from "@/components/layout/content-section";
import { ExportMenu } from "@/components/reports";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PurchaseOrderItemTable } from "@/features/purchase-orders/components/purchase-order-item-table";
import { PurchaseOrderLinkedBillsTable } from "@/features/purchase-orders/components/purchase-order-linked-bills-table";
import {
  PURCHASE_ORDER_BILLING_STATUS_LABELS,
  PURCHASE_ORDER_STATUS_BADGE_VARIANT,
  PURCHASE_ORDER_STATUS_LABELS,
} from "@/features/purchase-orders/constants/purchase-order-status";
import { useCancelPurchaseOrder } from "@/features/purchase-orders/hooks/use-cancel-purchase-order";
import { useConfirmPurchaseOrder } from "@/features/purchase-orders/hooks/use-confirm-purchase-order";
import { useDeletePurchaseOrder } from "@/features/purchase-orders/hooks/use-delete-purchase-order";
import { useFulfillPurchaseOrder } from "@/features/purchase-orders/hooks/use-fulfill-purchase-order";
import { usePurchaseOrder } from "@/features/purchase-orders/hooks/use-purchase-order";
import { useSupplierOptions } from "@/features/purchase-orders/hooks/use-supplier-options";
import { triggerPurchaseOrderDocumentDownload } from "@/features/purchase-orders/utils/trigger-purchase-order-document-download";
import { normalizeApiError } from "@/utils/api-error";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate, formatDateTime } from "@/utils/format-date";

/**
 * Read-only Purchase Order header view plus its line-item CRUD and full
 * lifecycle (confirm/cancel/fulfill/delete), mirroring
 * `PurchaseBillDetailPage`'s layout. Edit/Delete/Confirm are only ever
 * shown while `status === "draft"`; Fulfill/Cancel while `status ===
 * "confirmed"`; nothing while `fulfilled`/`cancelled` (terminal) - the
 * backend rejects every disallowed transition with its own 409/422, this
 * page doesn't preemptively block anything beyond hiding the actions, the
 * backend remains the actual authority.
 *
 * Every total shown (Subtotal/Discount/Taxable Amount/Tax/Transport Charge/
 * Other Charge/Round Off/Total Amount) is rendered straight from
 * `PurchaseOrderResponse` - never recomputed here. There is deliberately no
 * Paid Amount/Balance Amount/Outstanding figure anywhere on this page: a
 * purchase order is a procurement commitment, not a bill, and none of its
 * three lifecycle transitions ever touches supplier outstanding or ledger
 * (verified in the backend's own router docstrings) - preserving that
 * distinction in the UI is a hard business rule for this feature.
 *
 * `PurchaseOrderResponse` carries only `supplier_id`, so the ordering
 * supplier's display name is resolved via `useSupplierOptions()` - this
 * feature's own hook. The supplier name links to `/suppliers/{id}` only
 * when the caller holds `supplier:view`; otherwise it renders as plain
 * text rather than a dead link.
 *
 * The "Billing Status" section (Sprint 12 Session 12) shows the derived
 * Billed/Remaining/Status figures from linked Purchase Bills
 * (`GET /purchase-orders/{id}`'s own `billed_amount`/`remaining_amount`/
 * `billing_status`) - deliberately its own separate `ContentSection`, not
 * folded into the Totals `InfoCard` above: it describes billing progress
 * against Purchase Bills, a distinct concept from this order's own
 * financial totals, and must not be confused with the still-absent Paid/
 * Balance/Outstanding figures this page continues to never show.
 *
 * The "Purchase Bills" section (Sprint 12 Session 13,
 * `PurchaseOrderLinkedBillsTable`) lists every bill actually linked to this
 * order, below the item table - a read-only, single-request list, distinct
 * from the aggregate figures above it.
 */
export function PurchaseOrderDetailPage() {
  const params = useParams<{ id: string }>();
  const purchaseOrderId = params.id;
  const { hasPermission } = usePermissions();
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);
  const [isFulfillDialogOpen, setIsFulfillDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const purchaseOrderQuery = usePurchaseOrder(purchaseOrderId);
  const supplierOptions = useSupplierOptions();
  const confirmPurchaseOrder = useConfirmPurchaseOrder();
  const cancelPurchaseOrder = useCancelPurchaseOrder();
  const fulfillPurchaseOrder = useFulfillPurchaseOrder();
  const deletePurchaseOrder = useDeletePurchaseOrder();

  if (!hasPermission("purchase_order:view")) {
    return (
      <ErrorState
        title="You don't have permission to view purchase orders"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const order = purchaseOrderQuery.data;
  const apiError = purchaseOrderQuery.isError ? normalizeApiError(purchaseOrderQuery.error) : null;
  const supplierName = order ? (supplierOptions.nameById.get(order.supplierId) ?? "—") : undefined;
  const isDraft = order?.status === "draft";
  const isConfirmed = order?.status === "confirmed";
  const canCancel = (isDraft || isConfirmed) && hasPermission("purchase_order:cancel");

  const secondaryActions = order
    ? [
        isDraft && hasPermission("purchase_order:edit")
          ? { label: "Edit", icon: Pencil, href: `/purchase-orders/${order.id}/edit` }
          : null,
        canCancel ? { label: "Cancel", icon: Ban, onClick: () => setIsCancelDialogOpen(true) } : null,
        isDraft && hasPermission("purchase_order:delete")
          ? { label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) }
          : null,
      ].filter((action): action is NonNullable<typeof action> => action !== null)
    : undefined;

  return (
    <DetailPageTemplate
      title={order?.poNumber ?? "Draft Purchase Order"}
      description={supplierName}
      icon={ClipboardList}
      badge={
        order && (
          <Badge variant={PURCHASE_ORDER_STATUS_BADGE_VARIANT[order.status]}>
            {PURCHASE_ORDER_STATUS_LABELS[order.status]}
          </Badge>
        )
      }
      primaryAction={
        order && isDraft && hasPermission("purchase_order:confirm")
          ? { label: "Confirm Purchase Order", icon: CheckCircle2, onClick: () => setIsConfirmDialogOpen(true) }
          : order && isConfirmed && hasPermission("purchase_order:fulfill")
            ? { label: "Mark as Fulfilled", icon: PackageCheck, onClick: () => setIsFulfillDialogOpen(true) }
            : undefined
      }
      secondaryActions={secondaryActions && secondaryActions.length > 0 ? secondaryActions : undefined}
      exportMenu={
        // A purchase order only has a po_number once confirmed (or
        // confirmed-then-cancelled) - gating on poNumber directly (rather
        // than `!isDraft`) also correctly hides this for an order
        // cancelled straight from draft, which has no number either and
        // would otherwise 422 (backend: PURCHASE_ORDER_DOCUMENT_NOT_AVAILABLE).
        order && Boolean(order.poNumber) && hasPermission("purchase_order:view") ? (
          <ExportMenu
            label="Download Purchase Order"
            formats={["pdf"]}
            onExport={(format) => {
              if (format !== "pdf") return;
              triggerPurchaseOrderDocumentDownload(order.id);
            }}
          />
        ) : undefined
      }
      isLoading={purchaseOrderQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load purchase order record",
              description: apiError.message,
              onRetry: () => purchaseOrderQuery.refetch(),
            }
          : null
      }
    >
      {order && (
        <div className="space-y-6">
          <ContentSection title="Purchase Order Information">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <InfoCard title="Details">
                <DescriptionList
                  items={[
                    {
                      term: "Supplier",
                      details:
                        supplierName && hasPermission("supplier:view") ? (
                          <Link href={`/suppliers/${order.supplierId}`} className="hover:underline">
                            {supplierName}
                          </Link>
                        ) : (
                          (supplierName ?? "—")
                        ),
                    },
                    { term: "PO Number", details: order.poNumber ?? "Not yet confirmed" },
                    { term: "Status", details: PURCHASE_ORDER_STATUS_LABELS[order.status] },
                    { term: "PO Date", details: formatDate(order.orderDate) },
                    {
                      term: "Expected Delivery Date",
                      details: order.expectedDeliveryDate ? formatDate(order.expectedDeliveryDate) : "—",
                    },
                    {
                      term: "Confirmed At",
                      details: order.confirmedAt ? formatDateTime(order.confirmedAt) : "—",
                    },
                    { term: "Created At", details: formatDateTime(order.createdAt) },
                    { term: "Updated At", details: formatDateTime(order.updatedAt) },
                  ]}
                />
              </InfoCard>

              <InfoCard title="Totals">
                <DescriptionList
                  items={[
                    { term: "Subtotal", details: formatCurrency(order.subtotal) },
                    { term: "Discount", details: formatCurrency(order.discountAmount) },
                    { term: "Taxable Amount", details: formatCurrency(order.taxableAmount) },
                    { term: "Tax", details: formatCurrency(order.taxAmount) },
                    { term: "Transport Charge", details: formatCurrency(order.transportCharge) },
                    { term: "Other Charge", details: formatCurrency(order.otherCharge) },
                    { term: "Round Off", details: formatCurrency(order.roundOff) },
                    { term: "Total Amount", details: formatCurrency(order.totalAmount) },
                  ]}
                />
              </InfoCard>
            </div>
          </ContentSection>

          <ContentSection title="Billing Status">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard title="PO Total" value={formatCurrency(order.totalAmount)} />
              <MetricCard title="Billed" value={formatCurrency(order.billedAmount ?? "0")} />
              <MetricCard
                title="Remaining"
                value={formatCurrency(order.remainingAmount ?? order.totalAmount)}
              />
              <MetricCard
                title="Status"
                value={PURCHASE_ORDER_BILLING_STATUS_LABELS[order.billingStatus ?? "not_billed"]}
              />
            </div>
          </ContentSection>

          <InfoCard title="Remarks">
            {order.remarks ? (
              <p className="text-sm whitespace-pre-wrap">{order.remarks}</p>
            ) : (
              <EmptyState title="No remarks added" description="Remarks for this purchase order will appear here." />
            )}
          </InfoCard>

          <PurchaseOrderItemTable purchaseOrderId={order.id} purchaseOrderStatus={order.status} />

          <PurchaseOrderLinkedBillsTable purchaseOrderId={order.id} />

          <ConfirmationDialog
            open={isConfirmDialogOpen}
            onOpenChange={setIsConfirmDialogOpen}
            title="Confirm this purchase order?"
            description="This assigns a permanent PO number and locks the header and items from further changes. This action cannot be undone."
            confirmLabel="Confirm Purchase Order"
            isLoading={confirmPurchaseOrder.isPending}
            onConfirm={() =>
              confirmPurchaseOrder.mutate(order.id, { onSuccess: () => setIsConfirmDialogOpen(false) })
            }
          />

          <ConfirmationDialog
            open={isFulfillDialogOpen}
            onOpenChange={setIsFulfillDialogOpen}
            title="Mark this purchase order as fulfilled?"
            description="This marks the order as fulfilled and is a terminal state - no further edits, cancellation, or transitions are possible after this."
            confirmLabel="Mark as Fulfilled"
            isLoading={fulfillPurchaseOrder.isPending}
            onConfirm={() =>
              fulfillPurchaseOrder.mutate(order.id, { onSuccess: () => setIsFulfillDialogOpen(false) })
            }
          />

          <ConfirmationDialog
            open={isCancelDialogOpen}
            onOpenChange={setIsCancelDialogOpen}
            title="Cancel this purchase order?"
            description="This permanently cancels the order. Cancelled purchase orders cannot be edited, confirmed, or fulfilled. This action cannot be undone."
            confirmLabel="Cancel Purchase Order"
            variant="destructive"
            isLoading={cancelPurchaseOrder.isPending}
            onConfirm={() =>
              cancelPurchaseOrder.mutate(order.id, { onSuccess: () => setIsCancelDialogOpen(false) })
            }
          />

          <DeleteConfirmationDialog
            open={isDeleteDialogOpen}
            onOpenChange={setIsDeleteDialogOpen}
            entityName={order.poNumber ?? "this draft purchase order"}
            entityLabel="purchase order"
            isLoading={deletePurchaseOrder.isPending}
            onConfirm={() => deletePurchaseOrder.mutate(order.id)}
          />
        </div>
      )}
    </DetailPageTemplate>
  );
}
