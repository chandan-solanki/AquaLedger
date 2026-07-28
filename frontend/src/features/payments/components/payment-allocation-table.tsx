"use client";

import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { ContentSection } from "@/components/layout/content-section";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { invoiceKeys, invoiceService } from "@/features/invoices";
import type { Invoice } from "@/features/invoices";
import { getPaymentAllocationColumns } from "@/features/payments/components/payment-allocation-columns";
import { PaymentAllocationForm } from "@/features/payments/components/payment-allocation-form";
import { usePaymentAllocationRowActions } from "@/features/payments/components/payment-allocation-row-actions";
import { useCreatePaymentAllocation } from "@/features/payments/hooks/use-create-payment-allocation";
import { useDeletePaymentAllocation } from "@/features/payments/hooks/use-delete-payment-allocation";
import { usePaymentAllocation } from "@/features/payments/hooks/use-payment-allocation";
import { usePaymentAllocations } from "@/features/payments/hooks/use-payment-allocations";
import { useUpdatePaymentAllocation } from "@/features/payments/hooks/use-update-payment-allocation";
import type { PaymentAllocationFormValues } from "@/features/payments/components/payment-allocation-form";
import type { PaymentAllocation } from "@/features/payments/types/payment-allocation";
import type { PaymentStatus } from "@/features/payments/types/payment";
import { toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface PaymentAllocationTableProps {
  paymentId: string;
  paymentStatus: PaymentStatus;
  paymentCompanyId: string;
  paymentUnallocatedAmount: string;
}

/**
 * Resolves each allocated invoice's own fields (number, date, total,
 * balance) via Invoices' own public `invoiceService.getInvoice`
 * (`@/features/invoices`) - `PaymentAllocationResponse` carries only
 * `invoice_id` (app/modules/payments/schemas.py), and unlike Companies/Fish/
 * Boats there is no bounded "all invoices" options list to resolve against
 * (Invoices, like Trips, is an unbounded transactional resource) - so every
 * unique `invoice_id` on this payment's allocations is resolved individually
 * via `useQueries`, deduplicated and cached under the exact same
 * `invoiceKeys.detail(id)` key `useInvoice` itself uses, mirroring
 * `useTripNumbers` (`invoice-item-form.tsx`).
 */
function useAllocationInvoices(invoiceIds: string[]) {
  const uniqueIds = useMemo(() => Array.from(new Set(invoiceIds)), [invoiceIds]);
  const results = useQueries({
    queries: uniqueIds.map((id) => ({
      queryKey: invoiceKeys.detail(id),
      queryFn: () => invoiceService.getInvoice(id),
      staleTime: 5 * 60 * 1000,
    })),
  });

  return useMemo(() => {
    const map = new Map<string, Invoice>();
    uniqueIds.forEach((id, index) => {
      const invoice = results[index]?.data;
      if (invoice) map.set(id, invoice);
    });
    return map;
  }, [uniqueIds, results]);
}

/**
 * The Payment Detail page's Allocations section - list, add, edit and
 * delete for one payment's invoice allocations (Sprint 8 Session 3, see
 * TASKS.md). Add/Edit are plain shadcn `Dialog`s hosting the shared
 * `PaymentAllocationForm`, mirroring `InvoiceItemTable` - this session's
 * Routes scope is `/payments/[id]` only, so allocation CRUD stays inline on
 * this same page. Delete reuses the shared `DeleteConfirmationDialog`.
 *
 * Add/Edit/Delete are only ever offered while `paymentStatus === "draft"` -
 * the backend rejects every allocation mutation with 409
 * `PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT` otherwise
 * (app/modules/payments/service.py's `_ensure_draft_for_allocation`),
 * matching `03_INFORMATION_ARCHITECTURE.md` §13's "render only the
 * currently valid action" rule. Listing remains visible regardless of
 * status, matching the backend's own "allowed regardless of payment status"
 * list behavior.
 */
export function PaymentAllocationTable({
  paymentId,
  paymentStatus,
  paymentCompanyId,
  paymentUnallocatedAmount,
}: PaymentAllocationTableProps) {
  const { hasPermission } = usePermissions();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pendingEditId, setPendingEditId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PaymentAllocation | null>(null);

  const allocationsQuery = usePaymentAllocations(paymentId);
  const editAllocationQuery = usePaymentAllocation(paymentId, pendingEditId ?? undefined);
  const createAllocation = useCreatePaymentAllocation();
  const updateAllocation = useUpdatePaymentAllocation();
  const deleteAllocation = useDeletePaymentAllocation();

  const allocations = useMemo(() => allocationsQuery.data ?? [], [allocationsQuery.data]);
  const invoiceById = useAllocationInvoices(allocations.map((allocation) => allocation.invoiceId));
  const apiError = allocationsQuery.isError ? normalizeApiError(allocationsQuery.error) : null;
  const isDraft = paymentStatus === "draft";
  const canAdd = isDraft && hasPermission("payment:create");

  const rowActionsFor = usePaymentAllocationRowActions(
    (allocation) => setPendingEditId(allocation.id),
    (allocation) => setPendingDelete(allocation)
  );
  const columns = useMemo(
    () => getPaymentAllocationColumns(isDraft ? rowActionsFor : () => [], invoiceById),
    [isDraft, rowActionsFor, invoiceById]
  );
  const table = useDataTable({ data: allocations, columns });

  async function handleCreateSubmit(values: PaymentAllocationFormValues) {
    await createAllocation.mutateAsync({
      paymentId,
      payload: { invoice_id: values.invoice_id, allocated_amount: values.allocated_amount },
    });
    toastSuccess("Allocation added.");
    setIsCreateOpen(false);
  }

  async function handleEditSubmit(values: PaymentAllocationFormValues) {
    if (!pendingEditId || !editAllocationQuery.data) return;
    await updateAllocation.mutateAsync({
      paymentId,
      allocationId: pendingEditId,
      payload: { invoice_id: values.invoice_id, allocated_amount: values.allocated_amount },
      previousInvoiceId: editAllocationQuery.data.invoiceId,
    });
    toastSuccess("Allocation updated.");
    setPendingEditId(null);
  }

  return (
    <ContentSection
      title="Allocations"
      actions={
        canAdd ? (
          <Button size="sm" onClick={() => setIsCreateOpen(true)}>
            <Plus aria-hidden />
            Add Allocation
          </Button>
        ) : undefined
      }
    >
      <DataTable
        table={table}
        isLoading={allocationsQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load allocations",
                description: apiError.message,
                onRetry: () => allocationsQuery.refetch(),
              }
            : null
        }
        isEmpty={!allocationsQuery.isLoading && !apiError && allocations.length === 0}
        emptyState={
          <DataTableEmpty title="No allocations yet" description="Invoices this payment settles will appear here." />
        }
        stickyActionColumn
        aria-label="Payment allocations"
      />

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Add Allocation</DialogTitle>
          </DialogHeader>
          <PaymentAllocationForm
            companyId={paymentCompanyId}
            paymentUnallocatedAmount={paymentUnallocatedAmount}
            onSubmit={handleCreateSubmit}
            onCancel={() => setIsCreateOpen(false)}
            submitLabel="Add Allocation"
          />
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(pendingEditId)} onOpenChange={(open) => !open && setPendingEditId(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit Allocation</DialogTitle>
          </DialogHeader>
          {editAllocationQuery.data && (
            <PaymentAllocationForm
              companyId={paymentCompanyId}
              paymentUnallocatedAmount={paymentUnallocatedAmount}
              defaultValues={{
                invoice_id: editAllocationQuery.data.invoiceId,
                allocated_amount: editAllocationQuery.data.allocatedAmount,
              }}
              onSubmit={handleEditSubmit}
              onCancel={() => setPendingEditId(null)}
              submitLabel="Save Changes"
            />
          )}
        </DialogContent>
      </Dialog>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={invoiceById.get(pendingDelete.invoiceId)?.invoiceNumber ?? "this allocation"}
          entityLabel="allocation"
          isLoading={deleteAllocation.isPending}
          onConfirm={() =>
            deleteAllocation.mutate(
              { paymentId, allocationId: pendingDelete.id, invoiceId: pendingDelete.invoiceId },
              { onSuccess: () => setPendingDelete(null) }
            )
          }
        />
      )}
    </ContentSection>
  );
}
