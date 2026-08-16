"use client";

import { Ban, CheckCircle2, Pencil, PackageCheck, Trash2, Truck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { ContentSection } from "@/components/layout/content-section";
import { ExportMenu } from "@/components/reports";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { DeliveryChallanItemTable } from "@/features/delivery-challans/components/delivery-challan-item-table";
import {
  DELIVERY_CHALLAN_STATUS_BADGE_VARIANT,
  DELIVERY_CHALLAN_STATUS_LABELS,
} from "@/features/delivery-challans/constants/delivery-challan-status";
import { useCancelDeliveryChallan } from "@/features/delivery-challans/hooks/use-cancel-delivery-challan";
import { useDeleteDeliveryChallan } from "@/features/delivery-challans/hooks/use-delete-delivery-challan";
import { useDeliverDeliveryChallan } from "@/features/delivery-challans/hooks/use-deliver-delivery-challan";
import { useDeliveryChallan } from "@/features/delivery-challans/hooks/use-delivery-challan";
import { useDispatchDeliveryChallan } from "@/features/delivery-challans/hooks/use-dispatch-delivery-challan";
import { useInvoiceOptions } from "@/features/delivery-challans/hooks/use-invoice-options";
import { triggerDeliveryChallanDocumentDownload } from "@/features/delivery-challans/utils/trigger-delivery-challan-document-download";
import { normalizeApiError } from "@/utils/api-error";
import { formatDate, formatDateTime } from "@/utils/format-date";

/**
 * Read-only Delivery Challan header view plus its line-item CRUD and full
 * lifecycle (dispatch/deliver/cancel/delete), mirroring
 * `PurchaseOrderDetailPage`'s layout. Edit/Delete/Dispatch are only ever
 * shown while `status === "draft"`; Deliver while `status === "dispatched"`;
 * nothing while `delivered`/`cancelled` (terminal) - the backend rejects
 * every disallowed transition with its own 409/422, this page doesn't
 * preemptively block anything beyond hiding the actions, the backend
 * remains the actual authority.
 *
 * There is deliberately no financial figure anywhere on this page (no
 * balance, no outstanding, no paid amount) - a delivery challan is a
 * physical delivery record, not a financial settlement
 * (ARCHITECTURE.md §43); the linked Invoice's own financial state is only
 * ever one click away via the Invoice link below, never duplicated here.
 *
 * `DeliveryChallanResponse` carries only `invoice_id`, so the originating
 * invoice's number and billed customer's name are resolved via
 * `useInvoiceOptions()` - this feature's own hook. Both the Invoice and
 * Customer links only render as links when the caller holds
 * `invoice:view`/`company:view` respectively; otherwise they render as
 * plain text rather than a dead link.
 *
 * The PDF export (Sprint 12 Session 16) is only ever offered once the
 * challan carries a real `challanNumber` - assigned only at dispatch, the
 * same "gate on the number, not the status" rule the backend's own
 * `GET /{id}/document` enforces (DELIVERY_CHALLAN_DOCUMENT_NOT_AVAILABLE
 * otherwise) - so a dispatched, delivered, or dispatched-then-cancelled
 * challan can always download its document, but a still-draft or
 * cancelled-from-draft one never shows the option at all.
 */
export function DeliveryChallanDetailPage() {
  const params = useParams<{ id: string }>();
  const deliveryChallanId = params.id;
  const { hasPermission } = usePermissions();
  const [isDispatchDialogOpen, setIsDispatchDialogOpen] = useState(false);
  const [isDeliverDialogOpen, setIsDeliverDialogOpen] = useState(false);
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const deliveryChallanQuery = useDeliveryChallan(deliveryChallanId);
  const invoiceOptions = useInvoiceOptions();
  const dispatchDeliveryChallan = useDispatchDeliveryChallan();
  const deliverDeliveryChallan = useDeliverDeliveryChallan();
  const cancelDeliveryChallan = useCancelDeliveryChallan();
  const deleteDeliveryChallan = useDeleteDeliveryChallan();

  if (!hasPermission("delivery_challan:view")) {
    return (
      <ErrorState
        title="You don't have permission to view delivery challans"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const challan = deliveryChallanQuery.data;
  const apiError = deliveryChallanQuery.isError ? normalizeApiError(deliveryChallanQuery.error) : null;
  const invoice = challan ? invoiceOptions.invoiceById.get(challan.invoiceId) : undefined;
  const customerName = invoice ? (invoiceOptions.companyNameById.get(invoice.companyId) ?? "—") : undefined;
  const isDraft = challan?.status === "draft";
  const isDispatched = challan?.status === "dispatched";
  const canCancel = (isDraft || isDispatched) && hasPermission("delivery_challan:cancel");

  const secondaryActions = challan
    ? [
        isDraft && hasPermission("delivery_challan:edit")
          ? { label: "Edit", icon: Pencil, href: `/delivery-challans/${challan.id}/edit` }
          : null,
        canCancel ? { label: "Cancel", icon: Ban, onClick: () => setIsCancelDialogOpen(true) } : null,
        isDraft && hasPermission("delivery_challan:delete")
          ? { label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) }
          : null,
      ].filter((action): action is NonNullable<typeof action> => action !== null)
    : undefined;

  return (
    <DetailPageTemplate
      title={challan?.challanNumber ?? "Draft Delivery Challan"}
      description={customerName}
      icon={Truck}
      badge={
        challan && (
          <Badge variant={DELIVERY_CHALLAN_STATUS_BADGE_VARIANT[challan.status]}>
            {DELIVERY_CHALLAN_STATUS_LABELS[challan.status]}
          </Badge>
        )
      }
      primaryAction={
        challan && isDraft && hasPermission("delivery_challan:dispatch")
          ? { label: "Dispatch", icon: CheckCircle2, onClick: () => setIsDispatchDialogOpen(true) }
          : challan && isDispatched && hasPermission("delivery_challan:deliver")
            ? { label: "Mark as Delivered", icon: PackageCheck, onClick: () => setIsDeliverDialogOpen(true) }
            : undefined
      }
      secondaryActions={secondaryActions && secondaryActions.length > 0 ? secondaryActions : undefined}
      exportMenu={
        challan && Boolean(challan.challanNumber) && hasPermission("delivery_challan:view") ? (
          <ExportMenu
            label="Download Delivery Challan"
            formats={["pdf"]}
            onExport={(format) => {
              if (format !== "pdf") return;
              triggerDeliveryChallanDocumentDownload(challan.id);
            }}
          />
        ) : undefined
      }
      isLoading={deliveryChallanQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load delivery challan record",
              description: apiError.message,
              onRetry: () => deliveryChallanQuery.refetch(),
            }
          : null
      }
    >
      {challan && (
        <div className="space-y-6">
          <ContentSection title="Delivery Challan Information">
            <InfoCard title="Details">
              <DescriptionList
                items={[
                  {
                    term: "Invoice",
                    details:
                      invoice && hasPermission("invoice:view") ? (
                        <Link href={`/invoices/${invoice.id}`} className="hover:underline">
                          {invoice.invoiceNumber ?? "Draft Invoice"}
                        </Link>
                      ) : (
                        (invoice?.invoiceNumber ?? "—")
                      ),
                  },
                  {
                    term: "Customer",
                    details:
                      invoice && customerName && hasPermission("company:view") ? (
                        <Link href={`/companies/${invoice.companyId}`} className="hover:underline">
                          {customerName}
                        </Link>
                      ) : (
                        (customerName ?? "—")
                      ),
                  },
                  { term: "Challan Number", details: challan.challanNumber ?? "Not yet dispatched" },
                  { term: "Status", details: DELIVERY_CHALLAN_STATUS_LABELS[challan.status] },
                  { term: "Challan Date", details: formatDate(challan.challanDate) },
                  {
                    term: "Dispatched At",
                    details: challan.dispatchedAt ? formatDateTime(challan.dispatchedAt) : "—",
                  },
                  {
                    term: "Delivered At",
                    details: challan.deliveredAt ? formatDateTime(challan.deliveredAt) : "—",
                  },
                  { term: "Created At", details: formatDateTime(challan.createdAt) },
                  { term: "Updated At", details: formatDateTime(challan.updatedAt) },
                ]}
              />
            </InfoCard>
          </ContentSection>

          <InfoCard title="Remarks">
            {challan.remarks ? (
              <p className="text-sm whitespace-pre-wrap">{challan.remarks}</p>
            ) : (
              <EmptyState title="No remarks added" description="Remarks for this delivery challan will appear here." />
            )}
          </InfoCard>

          <DeliveryChallanItemTable
            deliveryChallanId={challan.id}
            deliveryChallanStatus={challan.status}
            invoiceId={challan.invoiceId}
          />

          <ConfirmationDialog
            open={isDispatchDialogOpen}
            onOpenChange={setIsDispatchDialogOpen}
            title="Dispatch this delivery challan?"
            description="This assigns a permanent challan number and locks the header and items from further changes. This action cannot be undone."
            confirmLabel="Dispatch"
            isLoading={dispatchDeliveryChallan.isPending}
            onConfirm={() =>
              dispatchDeliveryChallan.mutate(challan.id, { onSuccess: () => setIsDispatchDialogOpen(false) })
            }
          />

          <ConfirmationDialog
            open={isDeliverDialogOpen}
            onOpenChange={setIsDeliverDialogOpen}
            title="Mark this delivery challan as delivered?"
            description="This marks the challan as delivered and is a terminal state - no further edits, cancellation, or transitions are possible after this."
            confirmLabel="Mark as Delivered"
            isLoading={deliverDeliveryChallan.isPending}
            onConfirm={() =>
              deliverDeliveryChallan.mutate(challan.id, { onSuccess: () => setIsDeliverDialogOpen(false) })
            }
          />

          <ConfirmationDialog
            open={isCancelDialogOpen}
            onOpenChange={setIsCancelDialogOpen}
            title="Cancel this delivery challan?"
            description="This permanently cancels the delivery challan. Cancelled delivery challans cannot be edited, dispatched, or delivered. This action cannot be undone."
            confirmLabel="Cancel Delivery Challan"
            variant="destructive"
            isLoading={cancelDeliveryChallan.isPending}
            onConfirm={() =>
              cancelDeliveryChallan.mutate(challan.id, { onSuccess: () => setIsCancelDialogOpen(false) })
            }
          />

          <DeleteConfirmationDialog
            open={isDeleteDialogOpen}
            onOpenChange={setIsDeleteDialogOpen}
            entityName={challan.challanNumber ?? "this draft delivery challan"}
            entityLabel="delivery challan"
            isLoading={deleteDeliveryChallan.isPending}
            onConfirm={() => deleteDeliveryChallan.mutate(challan.id)}
          />
        </div>
      )}
    </DetailPageTemplate>
  );
}
