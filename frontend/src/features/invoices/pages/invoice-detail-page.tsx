"use client";

import { FileText, Pencil, Send, Trash2 } from "lucide-react";
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
import type { PageAction } from "@/components/layout/page-actions";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { useFishOptions } from "@/features/trips";
import { InvoiceIssueConflictDialog } from "@/features/invoices/components/invoice-issue-conflict-dialog";
import { InvoiceIssuePreflightDialog } from "@/features/invoices/components/invoice-issue-preflight-dialog";
import { InvoiceItemTable } from "@/features/invoices/components/invoice-item-table";
import { INVOICE_STATUS_BADGE_VARIANT, INVOICE_STATUS_LABELS } from "@/features/invoices/constants/invoice-status";
import { useCompanyOptions } from "@/features/invoices/hooks/use-company-options";
import { useDeleteInvoice } from "@/features/invoices/hooks/use-delete-invoice";
import { useInvoice } from "@/features/invoices/hooks/use-invoice";
import { useInvoiceIssuePreflight } from "@/features/invoices/hooks/use-invoice-issue-preflight";
import { useInvoiceItems } from "@/features/invoices/hooks/use-invoice-items";
import { useIssueInvoice } from "@/features/invoices/hooks/use-issue-invoice";
import type { InvoiceIssuePreflightConflict } from "@/features/invoices/types/invoice-issue-preflight";
import { triggerInvoiceDocumentDownload } from "@/features/invoices/utils/trigger-invoice-document-download";
import { normalizeApiError } from "@/utils/api-error";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate, formatDateTime } from "@/utils/format-date";

/**
 * Read-only Invoice header view, its line-item CRUD, and its lifecycle
 * actions (Sprint 7 Session 4, see TASKS.md) - Payments/PDF/Print/Email/
 * Credit Notes remain out of scope; there is no Cancel action because the
 * backend exposes no cancel endpoint yet ("invoice:cancel" is only a
 * seeded permission reserved for a future workflow, per
 * app/modules/invoices/permissions.py's own comment).
 *
 * Every action offered here mirrors a real, backend-enforced state-machine
 * rule (app/modules/invoices/service.py's `_ensure_draft`): Edit Header/
 * Add Item/Edit Item/Delete Item/Delete Invoice/Issue Invoice are only ever
 * shown while `status === "draft"` - once issued, the invoice and its items
 * become fully immutable (409 `INVOICE_NOT_DRAFT` on any attempt), so
 * hiding these actions post-issue is a UX convenience only; the backend
 * remains the actual authority (`07_FRONTEND_ARCHITECTURE.md` §11/§20).
 * Item-level gating already lives in `InvoiceItemTable` (Session 3) and is
 * unchanged here.
 *
 * Every total shown (Subtotal/Discount/Taxable Amount/Tax/Total/Paid/
 * Balance) is rendered straight from `InvoiceResponse` - never recomputed
 * here, per "the backend owns financial calculations." Issue's own effects
 * (invoice_number assignment, trip catch inventory deduction, company
 * outstanding_amount increase) are entirely server-computed; `useIssueInvoice`
 * only invalidates the affected queries so this page re-fetches the
 * server's own resulting numbers.
 *
 * `InvoiceResponse` carries only `company_id` (app/modules/invoices/schemas.py),
 * so the billed company's display name is resolved via
 * `useCompanyOptions()` - this feature's own hook, already built in
 * Session 1 for the List page's Company filter - not invented/joined here.
 */
export function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const invoiceId = params.id;
  const { hasPermission } = usePermissions();
  const [isIssueDialogOpen, setIsIssueDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [issueConflict, setIssueConflict] = useState<{ tripCatchId: string; requiredQuantity: string } | null>(
    null
  );
  const [preflightConflicts, setPreflightConflicts] = useState<InvoiceIssuePreflightConflict[] | null>(
    null
  );

  const invoiceQuery = useInvoice(invoiceId);
  const companyOptions = useCompanyOptions();
  const issueInvoice = useIssueInvoice();
  const deleteInvoice = useDeleteInvoice();
  const issuePreflight = useInvoiceIssuePreflight();
  // Shares InvoiceItemTable's own query cache (same queryKey) - never a second network request.
  const itemsQuery = useInvoiceItems(invoiceId);
  const fishOptions = useFishOptions();

  if (!hasPermission("invoice:view")) {
    return (
      <ErrorState
        title="You don't have permission to view invoices"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const invoice = invoiceQuery.data;
  const apiError = invoiceQuery.isError ? normalizeApiError(invoiceQuery.error) : null;
  const companyName = invoice ? (companyOptions.nameById.get(invoice.companyId) ?? "—") : undefined;
  const isDraft = invoice?.status === "draft";

  /**
   * Sprint 15 Session 10: runs one advisory preflight check before opening
   * the existing Issue confirmation dialog. A clean result (or no
   * conflicts) proceeds exactly as before Session 10; a conflicting result
   * opens the new warning dialog first. A FAILED preflight request (network
   * error, etc.) deliberately falls back to the existing confirmation flow
   * rather than blocking the user - this is advisory visibility only, never
   * an enforcement mechanism, so an unrelated hiccup fetching it must not
   * prevent a legitimate issue attempt the backend would happily accept.
   */
  function handleIssueClick() {
    if (!invoice) return;
    issuePreflight.mutate(invoice.id, {
      onSuccess: (result) => {
        if (result.canIssueNow) {
          setIsIssueDialogOpen(true);
        } else {
          setPreflightConflicts(result.conflicts);
        }
      },
      onError: () => {
        setIsIssueDialogOpen(true);
      },
    });
  }

  const secondaryActions: PageAction[] = [];
  if (invoice && isDraft && hasPermission("invoice:edit")) {
    secondaryActions.push({ label: "Edit", icon: Pencil, href: `/invoices/${invoice.id}/edit` });
  }
  if (invoice && isDraft && hasPermission("invoice:delete")) {
    secondaryActions.push({ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) });
  }

  return (
    <DetailPageTemplate
      title={invoice?.invoiceNumber ?? "Draft Invoice"}
      description={companyName}
      icon={FileText}
      badge={
        invoice && (
          <Badge variant={INVOICE_STATUS_BADGE_VARIANT[invoice.status]}>
            {INVOICE_STATUS_LABELS[invoice.status]}
          </Badge>
        )
      }
      primaryAction={
        invoice && isDraft && hasPermission("invoice:issue")
          ? {
              label: "Issue Invoice",
              icon: Send,
              onClick: handleIssueClick,
              loading: issuePreflight.isPending,
            }
          : undefined
      }
      secondaryActions={secondaryActions.length > 0 ? secondaryActions : undefined}
      exportMenu={
        // Only an issued invoice (or beyond) has an invoice_number to print -
        // a draft has nothing to download yet (backend: 422
        // INVOICE_DOCUMENT_NOT_AVAILABLE), so the button mirrors that same
        // backend-enforced rule the way Edit/Delete mirror DRAFT-only.
        invoice && !isDraft && hasPermission("invoice:view") ? (
          <ExportMenu
            label="Download Invoice"
            formats={["pdf"]}
            onExport={(format) => {
              if (format !== "pdf") return;
              triggerInvoiceDocumentDownload(invoice.id);
            }}
          />
        ) : undefined
      }
      isLoading={invoiceQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load invoice record",
              description: apiError.message,
              onRetry: () => invoiceQuery.refetch(),
            }
          : null
      }
    >
      {invoice && (
        <div className="space-y-6">
          <ContentSection title="Invoice Information">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <InfoCard title="Details">
                <DescriptionList
                  items={[
                    { term: "Company", details: companyName ?? "—" },
                    { term: "Invoice Number", details: invoice.invoiceNumber ?? "Not yet issued" },
                    { term: "Status", details: INVOICE_STATUS_LABELS[invoice.status] },
                    { term: "Invoice Date", details: formatDate(invoice.invoiceDate) },
                    { term: "Due Date", details: invoice.dueDate ? formatDate(invoice.dueDate) : "—" },
                    { term: "Created At", details: formatDateTime(invoice.createdAt) },
                    { term: "Updated At", details: formatDateTime(invoice.updatedAt) },
                  ]}
                />
              </InfoCard>

              <InfoCard title="Totals">
                <DescriptionList
                  items={[
                    { term: "Subtotal", details: formatCurrency(invoice.subtotal) },
                    { term: "Discount", details: formatCurrency(invoice.discountAmount) },
                    { term: "Taxable Amount", details: formatCurrency(invoice.taxableAmount) },
                    { term: "Tax", details: formatCurrency(invoice.taxAmount) },
                    { term: "Transport Charge", details: formatCurrency(invoice.transportCharge) },
                    { term: "Other Charge", details: formatCurrency(invoice.otherCharge) },
                    { term: "Round Off", details: formatCurrency(invoice.roundOff) },
                    { term: "Total Amount", details: formatCurrency(invoice.totalAmount) },
                    { term: "Paid Amount", details: formatCurrency(invoice.paidAmount) },
                    { term: "Balance Amount", details: formatCurrency(invoice.balanceAmount) },
                  ]}
                />
              </InfoCard>
            </div>
          </ContentSection>

          <InfoCard title="Remarks">
            {invoice.remarks ? (
              <p className="text-sm whitespace-pre-wrap">{invoice.remarks}</p>
            ) : (
              <EmptyState title="No remarks added" description="Remarks for this invoice will appear here." />
            )}
          </InfoCard>

          <InvoiceItemTable invoiceId={invoice.id} invoiceStatus={invoice.status} />

          <ConfirmationDialog
            open={isIssueDialogOpen}
            onOpenChange={setIsIssueDialogOpen}
            title="Issue this invoice?"
            description="This assigns a permanent invoice number, deducts the sold quantity from every referenced trip catch, and increases the company's outstanding balance. Once issued, the invoice and its items can no longer be edited or deleted. This action cannot be undone."
            confirmLabel="Issue Invoice"
            isLoading={issueInvoice.isPending}
            onConfirm={() =>
              issueInvoice.mutate(invoice.id, {
                onSuccess: () => setIsIssueDialogOpen(false),
                onError: (error) => {
                  const apiError = normalizeApiError(error);
                  const details = apiError.details as
                    | { trip_catch_id?: string; requested_quantity?: string }
                    | null
                    | undefined;
                  if (apiError.code === "INVOICE_INSUFFICIENT_INVENTORY" && details?.trip_catch_id) {
                    setIsIssueDialogOpen(false);
                    setIssueConflict({
                      tripCatchId: details.trip_catch_id,
                      requiredQuantity: details.requested_quantity ?? "",
                    });
                  }
                  // Any other failure (or a malformed/missing details payload) is already
                  // toasted generically by useIssueInvoice's own onError.
                },
              })
            }
          />

          {issueConflict && (
            <InvoiceIssueConflictDialog
              open={Boolean(issueConflict)}
              onOpenChange={(open) => !open && setIssueConflict(null)}
              currentInvoiceId={invoice.id}
              tripCatchId={issueConflict.tripCatchId}
              requiredQuantity={issueConflict.requiredQuantity}
            />
          )}

          {preflightConflicts && (
            <InvoiceIssuePreflightDialog
              open={Boolean(preflightConflicts)}
              onOpenChange={(open) => !open && setPreflightConflicts(null)}
              conflicts={preflightConflicts}
              items={itemsQuery.data ?? []}
              fishById={fishOptions.fishById}
              onContinueAnyway={() => {
                setPreflightConflicts(null);
                setIsIssueDialogOpen(true);
              }}
            />
          )}

          <DeleteConfirmationDialog
            open={isDeleteDialogOpen}
            onOpenChange={setIsDeleteDialogOpen}
            entityName={invoice.invoiceNumber ?? "this draft invoice"}
            entityLabel="invoice"
            isLoading={deleteInvoice.isPending}
            onConfirm={() => deleteInvoice.mutate(invoice.id)}
          />
        </div>
      )}
    </DetailPageTemplate>
  );
}
