"use client";

import { ArrowUpFromLine, Pencil, Send, Trash2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { ContentSection } from "@/components/layout/content-section";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import type { PageAction } from "@/components/layout/page-actions";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { SupplierPaymentAllocationTable } from "@/features/supplier-payments/components/supplier-payment-allocation-table";
import { SUPPLIER_PAYMENT_METHOD_LABELS } from "@/features/supplier-payments/constants/supplier-payment-method";
import {
  SUPPLIER_PAYMENT_STATUS_BADGE_VARIANT,
  SUPPLIER_PAYMENT_STATUS_LABELS,
} from "@/features/supplier-payments/constants/supplier-payment-status";
import { useDeleteSupplierPayment } from "@/features/supplier-payments/hooks/use-delete-supplier-payment";
import { usePostSupplierPayment } from "@/features/supplier-payments/hooks/use-post-supplier-payment";
import { useSupplierOptions } from "@/features/supplier-payments/hooks/use-supplier-options";
import { useSupplierPayment } from "@/features/supplier-payments/hooks/use-supplier-payment";
import { normalizeApiError } from "@/utils/api-error";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate, formatDateTime } from "@/utils/format-date";

/**
 * Read-only Supplier Payment header view, its allocation CRUD, and its
 * lifecycle actions (Sprint 9 Session 4, see TASKS.md) - Cancel/Refund
 * remain out of scope: the backend exposes no such endpoints
 * (app/modules/supplier_payments/router.py has exactly ten routes;
 * `SupplierPaymentStatus.CANCELLED` exists in the enum but nothing
 * transitions a payment to it).
 *
 * Every action offered here mirrors a real, backend-enforced state-machine
 * rule (app/modules/supplier_payments/service.py's `_ensure_draft`): Edit/
 * Delete/Post are only ever shown while `status === "draft"` - once posted,
 * the payment becomes fully immutable (409 `SUPPLIER_PAYMENT_NOT_DRAFT` on
 * any attempt), so hiding these actions post-posting is a UX convenience
 * only; the backend remains the actual authority
 * (`07_FRONTEND_ARCHITECTURE.md` §11/§20). Allocation-level gating already
 * lives in `SupplierPaymentAllocationTable` (driven by this same `status`)
 * and is unchanged here. Mirrors `PaymentDetailPage` exactly.
 *
 * Every amount shown (Amount/Allocated/Unallocated) is rendered straight
 * from `SupplierPaymentResponse` - never recomputed here, per "the backend
 * owns financial calculations." Post's own effect (payment_number
 * assignment) is entirely server-computed; `usePostSupplierPayment` only
 * invalidates the affected queries so this page re-fetches the server's own
 * resulting numbers.
 *
 * `SupplierPaymentResponse` carries only `supplier_id`
 * (app/modules/supplier_payments/schemas.py), so the paying supplier's
 * display name is resolved via `useSupplierOptions()` - this feature's own
 * hook, already built in Session 1 for the List page's Supplier filter -
 * not invented/joined here.
 */
export function SupplierPaymentDetailPage() {
  const params = useParams<{ id: string }>();
  const supplierPaymentId = params.id;
  const { hasPermission } = usePermissions();
  const [isPostDialogOpen, setIsPostDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const supplierPaymentQuery = useSupplierPayment(supplierPaymentId);
  const supplierOptions = useSupplierOptions();
  const postSupplierPayment = usePostSupplierPayment();
  const deleteSupplierPayment = useDeleteSupplierPayment();

  if (!hasPermission("supplier_payment:view")) {
    return (
      <ErrorState
        title="You don't have permission to view supplier payments"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const payment = supplierPaymentQuery.data;
  const apiError = supplierPaymentQuery.isError ? normalizeApiError(supplierPaymentQuery.error) : null;
  const supplierName = payment ? (supplierOptions.nameById.get(payment.supplierId) ?? "—") : undefined;
  const isDraft = payment?.status === "draft";

  const secondaryActions: PageAction[] = [];
  if (payment && isDraft && hasPermission("supplier_payment:edit")) {
    secondaryActions.push({ label: "Edit", icon: Pencil, href: `/supplier-payments/${payment.id}/edit` });
  }
  if (payment && isDraft && hasPermission("supplier_payment:delete")) {
    secondaryActions.push({ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) });
  }

  return (
    <DetailPageTemplate
      title={payment?.paymentNumber ?? "Draft Supplier Payment"}
      description={supplierName}
      icon={ArrowUpFromLine}
      badge={
        payment && (
          <Badge variant={SUPPLIER_PAYMENT_STATUS_BADGE_VARIANT[payment.status]}>
            {SUPPLIER_PAYMENT_STATUS_LABELS[payment.status]}
          </Badge>
        )
      }
      primaryAction={
        payment && isDraft && hasPermission("supplier_payment:post")
          ? { label: "Post Payment", icon: Send, onClick: () => setIsPostDialogOpen(true) }
          : undefined
      }
      secondaryActions={secondaryActions.length > 0 ? secondaryActions : undefined}
      isLoading={supplierPaymentQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load supplier payment record",
              description: apiError.message,
              onRetry: () => supplierPaymentQuery.refetch(),
            }
          : null
      }
    >
      {payment && (
        <div className="space-y-6">
          <ContentSection title="Payment Information">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <InfoCard title="Details">
                <DescriptionList
                  items={[
                    { term: "Supplier", details: supplierName ?? "—" },
                    { term: "Payment Number", details: payment.paymentNumber ?? "Not yet posted" },
                    { term: "Status", details: SUPPLIER_PAYMENT_STATUS_LABELS[payment.status] },
                    { term: "Method", details: SUPPLIER_PAYMENT_METHOD_LABELS[payment.paymentMethod] },
                    { term: "Payment Date", details: formatDate(payment.paymentDate) },
                    { term: "Reference Number", details: payment.referenceNumber ?? "—" },
                    { term: "Bank Name", details: payment.bankName ?? "—" },
                    { term: "Created At", details: formatDateTime(payment.createdAt) },
                    { term: "Updated At", details: formatDateTime(payment.updatedAt) },
                  ]}
                />
              </InfoCard>

              <InfoCard title="Amounts">
                <DescriptionList
                  items={[
                    { term: "Amount", details: formatCurrency(payment.amount) },
                    { term: "Allocated", details: formatCurrency(payment.allocatedAmount) },
                    { term: "Unallocated", details: formatCurrency(payment.unallocatedAmount) },
                  ]}
                />
              </InfoCard>
            </div>
          </ContentSection>

          <InfoCard title="Remarks">
            {payment.remarks ? (
              <p className="text-sm whitespace-pre-wrap">{payment.remarks}</p>
            ) : (
              <EmptyState
                title="No remarks added"
                description="Remarks for this supplier payment will appear here."
              />
            )}
          </InfoCard>

          <SupplierPaymentAllocationTable
            supplierPaymentId={payment.id}
            supplierPaymentStatus={payment.status}
            supplierId={payment.supplierId}
            paymentUnallocatedAmount={payment.unallocatedAmount}
          />

          <ConfirmationDialog
            open={isPostDialogOpen}
            onOpenChange={setIsPostDialogOpen}
            title="Post this supplier payment?"
            description="This assigns a permanent payment number and locks the payment. Once posted, it can no longer be edited, deleted, or have its allocations changed. This action cannot be undone."
            confirmLabel="Post Payment"
            isLoading={postSupplierPayment.isPending}
            onConfirm={() =>
              postSupplierPayment.mutate(payment.id, { onSuccess: () => setIsPostDialogOpen(false) })
            }
          />

          <DeleteConfirmationDialog
            open={isDeleteDialogOpen}
            onOpenChange={setIsDeleteDialogOpen}
            entityName={payment.paymentNumber ?? "this draft supplier payment"}
            entityLabel="supplier payment"
            isLoading={deleteSupplierPayment.isPending}
            onConfirm={() => deleteSupplierPayment.mutate(payment.id)}
          />
        </div>
      )}
    </DetailPageTemplate>
  );
}
