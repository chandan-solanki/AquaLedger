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
import { getSupplierPaymentAllocationColumns } from "@/features/supplier-payments/components/supplier-payment-allocation-columns";
import { SupplierPaymentAllocationForm } from "@/features/supplier-payments/components/supplier-payment-allocation-form";
import type { SupplierPaymentAllocationFormValues } from "@/features/supplier-payments/components/supplier-payment-allocation-form";
import { useSupplierPaymentAllocationRowActions } from "@/features/supplier-payments/components/supplier-payment-allocation-row-actions";
import { useCreateSupplierPaymentAllocation } from "@/features/supplier-payments/hooks/use-create-supplier-payment-allocation";
import { useDeleteSupplierPaymentAllocation } from "@/features/supplier-payments/hooks/use-delete-supplier-payment-allocation";
import { useSupplierPaymentAllocation } from "@/features/supplier-payments/hooks/use-supplier-payment-allocation";
import { useSupplierPaymentAllocations } from "@/features/supplier-payments/hooks/use-supplier-payment-allocations";
import { useUpdateSupplierPaymentAllocation } from "@/features/supplier-payments/hooks/use-update-supplier-payment-allocation";
import { purchaseBillKeys, purchaseBillService } from "@/features/purchase-bills";
import type { PurchaseBill } from "@/features/purchase-bills";
import type { SupplierPaymentAllocation } from "@/features/supplier-payments/types/supplier-payment-allocation";
import type { SupplierPaymentStatus } from "@/features/supplier-payments/types/supplier-payment";
import { toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface SupplierPaymentAllocationTableProps {
  supplierPaymentId: string;
  supplierPaymentStatus: SupplierPaymentStatus;
  supplierId: string;
  paymentUnallocatedAmount: string;
}

/**
 * Resolves each allocated purchase bill's own fields (number, date, total,
 * balance) via the Purchase Bills feature's own public
 * `purchaseBillService.getPurchaseBill` (`@/features/purchase-bills`) -
 * `SupplierPaymentAllocationResponse` carries only `purchase_bill_id`
 * (app/modules/supplier_payments/schemas.py), and unlike Companies/Fish/
 * Boats there is no bounded "all purchase bills" options list to resolve
 * against (Purchase Bills, like Invoices, is an unbounded transactional
 * resource) - so every unique `purchase_bill_id` on this payment's
 * allocations is resolved individually via `useQueries`, deduplicated and
 * cached under the exact same `purchaseBillKeys.detail(id)` key the
 * Allocation form's selector itself uses, mirroring `useAllocationInvoices`
 * (`payment-allocation-table.tsx`).
 */
function useAllocationPurchaseBills(purchaseBillIds: string[]) {
  const uniqueIds = useMemo(() => Array.from(new Set(purchaseBillIds)), [purchaseBillIds]);
  const results = useQueries({
    queries: uniqueIds.map((id) => ({
      queryKey: purchaseBillKeys.detail(id),
      queryFn: () => purchaseBillService.getPurchaseBill(id),
      staleTime: 5 * 60 * 1000,
    })),
  });

  return useMemo(() => {
    const map = new Map<string, PurchaseBill>();
    uniqueIds.forEach((id, index) => {
      const bill = results[index]?.data;
      if (bill) map.set(id, bill);
    });
    return map;
  }, [uniqueIds, results]);
}

/**
 * The Supplier Payment Detail page's Allocations section - list, add, edit
 * and delete for one supplier payment's purchase bill allocations (Sprint 9
 * Session 3, see TASKS.md). Add/Edit are plain shadcn `Dialog`s hosting the
 * shared `SupplierPaymentAllocationForm`, mirroring `PaymentAllocationTable`
 * - this session's Routes scope is `/supplier-payments/[id]` only, so
 * allocation CRUD stays inline on this same page. Delete reuses the shared
 * `DeleteConfirmationDialog`.
 *
 * Add/Edit/Delete are only ever offered while `supplierPaymentStatus ===
 * "draft"` - the backend rejects every allocation mutation with 409
 * `SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT` otherwise
 * (app/modules/supplier_payments/service.py's
 * `_ensure_draft_for_allocation`), matching
 * `03_INFORMATION_ARCHITECTURE.md` §13's "render only the currently valid
 * action" rule. Listing remains visible regardless of status, matching the
 * backend's own "allowed regardless of payment status" list behavior.
 */
export function SupplierPaymentAllocationTable({
  supplierPaymentId,
  supplierPaymentStatus,
  supplierId,
  paymentUnallocatedAmount,
}: SupplierPaymentAllocationTableProps) {
  const { hasPermission } = usePermissions();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pendingEditId, setPendingEditId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<SupplierPaymentAllocation | null>(null);

  const allocationsQuery = useSupplierPaymentAllocations(supplierPaymentId);
  const editAllocationQuery = useSupplierPaymentAllocation(supplierPaymentId, pendingEditId ?? undefined);
  const createAllocation = useCreateSupplierPaymentAllocation();
  const updateAllocation = useUpdateSupplierPaymentAllocation();
  const deleteAllocation = useDeleteSupplierPaymentAllocation();

  const allocations = useMemo(() => allocationsQuery.data ?? [], [allocationsQuery.data]);
  const purchaseBillById = useAllocationPurchaseBills(
    allocations.map((allocation) => allocation.purchaseBillId)
  );
  const apiError = allocationsQuery.isError ? normalizeApiError(allocationsQuery.error) : null;
  const isDraft = supplierPaymentStatus === "draft";
  const canAdd = isDraft && hasPermission("supplier_payment:create");

  const rowActionsFor = useSupplierPaymentAllocationRowActions(
    (allocation) => setPendingEditId(allocation.id),
    (allocation) => setPendingDelete(allocation)
  );
  const columns = useMemo(
    () => getSupplierPaymentAllocationColumns(isDraft ? rowActionsFor : () => [], purchaseBillById),
    [isDraft, rowActionsFor, purchaseBillById]
  );
  const table = useDataTable({ data: allocations, columns });

  async function handleCreateSubmit(values: SupplierPaymentAllocationFormValues) {
    await createAllocation.mutateAsync({
      supplierPaymentId,
      payload: { purchase_bill_id: values.purchase_bill_id, allocated_amount: values.allocated_amount },
    });
    toastSuccess("Allocation added.");
    setIsCreateOpen(false);
  }

  async function handleEditSubmit(values: SupplierPaymentAllocationFormValues) {
    if (!pendingEditId || !editAllocationQuery.data) return;
    await updateAllocation.mutateAsync({
      supplierPaymentId,
      allocationId: pendingEditId,
      payload: { purchase_bill_id: values.purchase_bill_id, allocated_amount: values.allocated_amount },
      previousPurchaseBillId: editAllocationQuery.data.purchaseBillId,
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
          <DataTableEmpty
            title="No allocations yet"
            description="Purchase bills this payment settles will appear here."
          />
        }
        stickyActionColumn
        aria-label="Supplier payment allocations"
      />

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Add Allocation</DialogTitle>
          </DialogHeader>
          <SupplierPaymentAllocationForm
            supplierId={supplierId}
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
            <SupplierPaymentAllocationForm
              supplierId={supplierId}
              paymentUnallocatedAmount={paymentUnallocatedAmount}
              defaultValues={{
                purchase_bill_id: editAllocationQuery.data.purchaseBillId,
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
          entityName={purchaseBillById.get(pendingDelete.purchaseBillId)?.billNumber ?? "this allocation"}
          entityLabel="allocation"
          isLoading={deleteAllocation.isPending}
          onConfirm={() =>
            deleteAllocation.mutate(
              {
                supplierPaymentId,
                allocationId: pendingDelete.id,
                purchaseBillId: pendingDelete.purchaseBillId,
              },
              { onSuccess: () => setPendingDelete(null) }
            )
          }
        />
      )}
    </ContentSection>
  );
}
