"use client";

import { FileText, Pencil, Send } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { ContentSection } from "@/components/layout/content-section";
import { ExportMenu } from "@/components/reports";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { usePurchaseOrder } from "@/features/purchase-orders";
import { PurchaseBillItemTable } from "@/features/purchase-bills/components/purchase-bill-item-table";
import {
  PURCHASE_BILL_STATUS_BADGE_VARIANT,
  PURCHASE_BILL_STATUS_LABELS,
} from "@/features/purchase-bills/constants/purchase-bill-status";
import { usePostPurchaseBill } from "@/features/purchase-bills/hooks/use-post-purchase-bill";
import { usePurchaseBill } from "@/features/purchase-bills/hooks/use-purchase-bill";
import { useSupplierOptions } from "@/features/purchase-bills/hooks/use-supplier-options";
import { triggerPurchaseBillDocumentDownload } from "@/features/purchase-bills/utils/trigger-purchase-bill-document-download";
import { normalizeApiError } from "@/utils/api-error";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate, formatDateTime } from "@/utils/format-date";

/**
 * Read-only Purchase Bill header view plus its line-item CRUD and posting
 * lifecycle action - no Delete (that remains separate, later work),
 * mirroring `InvoiceDetailPage`'s layout minus its own Delete action.
 * Edit/Post are only ever shown while `status === "draft"` - the backend
 * rejects both with 409 `PURCHASE_BILL_NOT_DRAFT` otherwise
 * (app/modules/purchase/service.py's `_ensure_draft`); this page doesn't
 * preemptively block anything beyond hiding the actions, the backend
 * remains the actual authority.
 *
 * Posting is the module's one true business transaction - a purchase bill
 * created via `PurchaseBillForm` starts `draft` and stays invisible to the
 * Supplier Payment Allocation selector (which only offers `posted`/
 * `partially_paid` bills) until posted, so this action is what actually
 * unblocks that downstream workflow.
 *
 * Every total shown (Subtotal/Discount/Taxable Amount/Tax/Total/Paid/
 * Balance) is rendered straight from `PurchaseBillResponse` - never
 * recomputed here, per "the backend owns financial calculations." Post's
 * own effects (bill_number assignment, supplier outstanding_amount
 * increase) are entirely server-computed; `usePostPurchaseBill` only
 * invalidates the affected queries so this page re-fetches the server's
 * own resulting numbers. Item-level gating already lives in
 * `PurchaseBillItemTable` (driven by this same `status`) and is unchanged
 * here.
 *
 * `PurchaseBillResponse` carries only `supplier_id`
 * (app/modules/purchase/schemas.py), so the billing supplier's display name
 * is resolved via `useSupplierOptions()` - this feature's own hook, already
 * built for the List page's Supplier filter - not invented/joined here.
 */
export function PurchaseBillDetailPage() {
  const params = useParams<{ id: string }>();
  const purchaseBillId = params.id;
  const { hasPermission } = usePermissions();
  const [isPostDialogOpen, setIsPostDialogOpen] = useState(false);

  const purchaseBillQuery = usePurchaseBill(purchaseBillId);
  const supplierOptions = useSupplierOptions();
  const postPurchaseBill = usePostPurchaseBill();
  const linkedPurchaseOrderQuery = usePurchaseOrder(purchaseBillQuery.data?.purchaseOrderId ?? undefined);

  if (!hasPermission("purchase:view")) {
    return (
      <ErrorState
        title="You don't have permission to view purchase bills"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const bill = purchaseBillQuery.data;
  const apiError = purchaseBillQuery.isError ? normalizeApiError(purchaseBillQuery.error) : null;
  const supplierName = bill ? (supplierOptions.nameById.get(bill.supplierId) ?? "—") : undefined;
  const isDraft = bill?.status === "draft";

  return (
    <DetailPageTemplate
      title={bill?.billNumber ?? "Draft Purchase Bill"}
      description={supplierName}
      icon={FileText}
      badge={
        bill && (
          <Badge variant={PURCHASE_BILL_STATUS_BADGE_VARIANT[bill.status]}>
            {PURCHASE_BILL_STATUS_LABELS[bill.status]}
          </Badge>
        )
      }
      primaryAction={
        bill && isDraft && hasPermission("purchase:post")
          ? { label: "Post Purchase Bill", icon: Send, onClick: () => setIsPostDialogOpen(true) }
          : undefined
      }
      secondaryActions={
        bill && isDraft && hasPermission("purchase:edit")
          ? [{ label: "Edit", icon: Pencil, href: `/purchase-bills/${bill.id}/edit` }]
          : undefined
      }
      exportMenu={
        // Only a posted bill (or beyond) has a bill_number to print - a
        // draft has nothing to download yet (backend: 422
        // PURCHASE_BILL_DOCUMENT_NOT_AVAILABLE), so the button mirrors
        // that same backend-enforced rule the way Edit mirrors DRAFT-only.
        bill && !isDraft && hasPermission("purchase:view") ? (
          <ExportMenu
            label="Download Purchase Bill"
            formats={["pdf"]}
            onExport={(format) => {
              if (format !== "pdf") return;
              triggerPurchaseBillDocumentDownload(bill.id);
            }}
          />
        ) : undefined
      }
      isLoading={purchaseBillQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load purchase bill record",
              description: apiError.message,
              onRetry: () => purchaseBillQuery.refetch(),
            }
          : null
      }
    >
      {bill && (
        <div className="space-y-6">
          <ContentSection title="Purchase Bill Information">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <InfoCard title="Details">
                <DescriptionList
                  items={[
                    { term: "Supplier", details: supplierName ?? "—" },
                    {
                      term: "Purchase Order",
                      details: bill.purchaseOrderId ? (
                        hasPermission("purchase_order:view") ? (
                          <Link href={`/purchase-orders/${bill.purchaseOrderId}`} className="hover:underline">
                            {linkedPurchaseOrderQuery.data?.poNumber ?? "View purchase order"}
                          </Link>
                        ) : (
                          (linkedPurchaseOrderQuery.data?.poNumber ?? "Linked purchase order")
                        )
                      ) : (
                        "—"
                      ),
                    },
                    { term: "Bill Number", details: bill.billNumber ?? "Not yet posted" },
                    { term: "Status", details: PURCHASE_BILL_STATUS_LABELS[bill.status] },
                    { term: "Bill Date", details: formatDate(bill.billDate) },
                    { term: "Due Date", details: bill.dueDate ? formatDate(bill.dueDate) : "—" },
                    { term: "Created At", details: formatDateTime(bill.createdAt) },
                    { term: "Updated At", details: formatDateTime(bill.updatedAt) },
                  ]}
                />
              </InfoCard>

              <InfoCard title="Totals">
                <DescriptionList
                  items={[
                    { term: "Subtotal", details: formatCurrency(bill.subtotal) },
                    { term: "Discount", details: formatCurrency(bill.discountAmount) },
                    { term: "Taxable Amount", details: formatCurrency(bill.taxableAmount) },
                    { term: "Tax", details: formatCurrency(bill.taxAmount) },
                    { term: "Transport Charge", details: formatCurrency(bill.transportCharge) },
                    { term: "Other Charge", details: formatCurrency(bill.otherCharge) },
                    { term: "Round Off", details: formatCurrency(bill.roundOff) },
                    { term: "Total Amount", details: formatCurrency(bill.totalAmount) },
                    { term: "Paid Amount", details: formatCurrency(bill.paidAmount) },
                    { term: "Balance Amount", details: formatCurrency(bill.balanceAmount) },
                  ]}
                />
              </InfoCard>
            </div>
          </ContentSection>

          <InfoCard title="Remarks">
            {bill.remarks ? (
              <p className="text-sm whitespace-pre-wrap">{bill.remarks}</p>
            ) : (
              <EmptyState title="No remarks added" description="Remarks for this purchase bill will appear here." />
            )}
          </InfoCard>

          <PurchaseBillItemTable
            purchaseBillId={bill.id}
            purchaseBillStatus={bill.status}
            purchaseOrderId={bill.purchaseOrderId}
          />

          <ConfirmationDialog
            open={isPostDialogOpen}
            onOpenChange={setIsPostDialogOpen}
            title="Post this purchase bill?"
            description="This assigns a permanent bill number and increases your supplier's outstanding balance by this bill's balance amount. Once posted, the bill and its items can no longer be edited or deleted. This action cannot be undone."
            confirmLabel="Post Purchase Bill"
            isLoading={postPurchaseBill.isPending}
            onConfirm={() =>
              postPurchaseBill.mutate(bill.id, { onSuccess: () => setIsPostDialogOpen(false) })
            }
          />
        </div>
      )}
    </DetailPageTemplate>
  );
}
