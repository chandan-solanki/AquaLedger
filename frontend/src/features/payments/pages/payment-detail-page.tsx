"use client";

import { ArrowDownToLine, Pencil, Send, Trash2 } from "lucide-react";
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
import { PaymentAllocationTable } from "@/features/payments/components/payment-allocation-table";
import { PAYMENT_METHOD_LABELS } from "@/features/payments/constants/payment-method";
import { PAYMENT_STATUS_BADGE_VARIANT, PAYMENT_STATUS_LABELS } from "@/features/payments/constants/payment-status";
import { useCompanyOptions } from "@/features/payments/hooks/use-company-options";
import { useDeletePayment } from "@/features/payments/hooks/use-delete-payment";
import { usePayment } from "@/features/payments/hooks/use-payment";
import { usePostPayment } from "@/features/payments/hooks/use-post-payment";
import { normalizeApiError } from "@/utils/api-error";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate, formatDateTime } from "@/utils/format-date";

/**
 * Read-only Payment header view, its allocation CRUD, and its lifecycle
 * actions (Sprint 8 Session 4, see TASKS.md) - Cancel/Refund remain out of
 * scope: the backend exposes no such endpoints
 * (app/modules/payments/router.py has exactly ten routes; `PaymentStatus.
 * CANCELLED` exists in the enum but nothing transitions a payment to it).
 *
 * Every action offered here mirrors a real, backend-enforced state-machine
 * rule (app/modules/payments/service.py's `_ensure_draft`): Edit/Delete/
 * Post are only ever shown while `status === "draft"` - once posted, the
 * payment becomes fully immutable (409 `PAYMENT_NOT_DRAFT` on any attempt),
 * so hiding these actions post-posting is a UX convenience only; the
 * backend remains the actual authority (`07_FRONTEND_ARCHITECTURE.md`
 * §11/§20). Allocation-level gating already lives in
 * `PaymentAllocationTable` (Session 3, driven by this same `status`) and is
 * unchanged here.
 *
 * Every amount shown (Amount/Allocated/Unallocated) is rendered straight
 * from `PaymentResponse` - never recomputed here, per "the backend owns
 * financial calculations." Post's own effect (payment_number assignment) is
 * entirely server-computed; `usePostPayment` only invalidates the affected
 * queries so this page re-fetches the server's own resulting numbers.
 *
 * `PaymentResponse` carries only `company_id` (app/modules/payments/schemas.py),
 * so the paying company's display name is resolved via `useCompanyOptions()`
 * - this feature's own hook, already built in Session 1 for the List page's
 * Company filter - not invented/joined here.
 */
export function PaymentDetailPage() {
  const params = useParams<{ id: string }>();
  const paymentId = params.id;
  const { hasPermission } = usePermissions();
  const [isPostDialogOpen, setIsPostDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const paymentQuery = usePayment(paymentId);
  const companyOptions = useCompanyOptions();
  const postPayment = usePostPayment();
  const deletePayment = useDeletePayment();

  if (!hasPermission("payment:view")) {
    return (
      <ErrorState
        title="You don't have permission to view payments"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const payment = paymentQuery.data;
  const apiError = paymentQuery.isError ? normalizeApiError(paymentQuery.error) : null;
  const companyName = payment ? (companyOptions.nameById.get(payment.companyId) ?? "—") : undefined;
  const isDraft = payment?.status === "draft";

  const secondaryActions: PageAction[] = [];
  if (payment && isDraft && hasPermission("payment:edit")) {
    secondaryActions.push({ label: "Edit", icon: Pencil, href: `/payments/${payment.id}/edit` });
  }
  if (payment && isDraft && hasPermission("payment:delete")) {
    secondaryActions.push({ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) });
  }

  return (
    <DetailPageTemplate
      title={payment?.paymentNumber ?? "Draft Payment"}
      description={companyName}
      icon={ArrowDownToLine}
      badge={
        payment && (
          <Badge variant={PAYMENT_STATUS_BADGE_VARIANT[payment.status]}>
            {PAYMENT_STATUS_LABELS[payment.status]}
          </Badge>
        )
      }
      primaryAction={
        payment && isDraft && hasPermission("payment:post")
          ? { label: "Post Payment", icon: Send, onClick: () => setIsPostDialogOpen(true) }
          : undefined
      }
      secondaryActions={secondaryActions.length > 0 ? secondaryActions : undefined}
      isLoading={paymentQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load payment record",
              description: apiError.message,
              onRetry: () => paymentQuery.refetch(),
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
                    { term: "Customer", details: companyName ?? "—" },
                    { term: "Payment Number", details: payment.paymentNumber ?? "Not yet posted" },
                    { term: "Status", details: PAYMENT_STATUS_LABELS[payment.status] },
                    { term: "Method", details: PAYMENT_METHOD_LABELS[payment.paymentMethod] },
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
              <EmptyState title="No remarks added" description="Remarks for this payment will appear here." />
            )}
          </InfoCard>

          <PaymentAllocationTable
            paymentId={payment.id}
            paymentStatus={payment.status}
            paymentCompanyId={payment.companyId}
            paymentUnallocatedAmount={payment.unallocatedAmount}
          />

          <ConfirmationDialog
            open={isPostDialogOpen}
            onOpenChange={setIsPostDialogOpen}
            title="Post this payment?"
            description="This assigns a permanent payment number and locks the payment. Once posted, it can no longer be edited, deleted, or have its allocations changed. This action cannot be undone."
            confirmLabel="Post Payment"
            isLoading={postPayment.isPending}
            onConfirm={() =>
              postPayment.mutate(payment.id, { onSuccess: () => setIsPostDialogOpen(false) })
            }
          />

          <DeleteConfirmationDialog
            open={isDeleteDialogOpen}
            onOpenChange={setIsDeleteDialogOpen}
            entityName={payment.paymentNumber ?? "this draft payment"}
            entityLabel="payment"
            isLoading={deletePayment.isPending}
            onConfirm={() => deletePayment.mutate(payment.id)}
          />
        </div>
      )}
    </DetailPageTemplate>
  );
}
