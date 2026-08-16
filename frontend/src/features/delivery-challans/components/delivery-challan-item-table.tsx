"use client";

import { Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { ContentSection } from "@/components/layout/content-section";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import {
  buildDeliveryChallanItemRows,
  getDeliveryChallanItemColumns,
  type DeliveryChallanItemRow,
} from "@/features/delivery-challans/components/delivery-challan-item-columns";
import { DeliveryChallanItemForm } from "@/features/delivery-challans/components/delivery-challan-item-form";
import { useDeliveryChallanItemRowActions } from "@/features/delivery-challans/components/delivery-challan-item-row-actions";
import { useCreateDeliveryChallanItem } from "@/features/delivery-challans/hooks/use-create-delivery-challan-item";
import { useDeleteDeliveryChallanItem } from "@/features/delivery-challans/hooks/use-delete-delivery-challan-item";
import { useDeliveryChallanItems } from "@/features/delivery-challans/hooks/use-delivery-challan-items";
import { useInvoiceDeliverySummary } from "@/features/delivery-challans/hooks/use-invoice-delivery-summary";
import { useUpdateDeliveryChallanItem } from "@/features/delivery-challans/hooks/use-update-delivery-challan-item";
import {
  toDeliveryChallanItemFormValues,
  toDeliveryChallanItemRequestPayload,
  toDeliveryChallanItemUpdatePayload,
  type DeliveryChallanItemFormValues,
} from "@/features/delivery-challans/schemas/delivery-challan-item-form-schema";
import type { DeliveryChallanStatus } from "@/features/delivery-challans/types/delivery-challan";
import { toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface DeliveryChallanItemTableProps {
  deliveryChallanId: string;
  deliveryChallanStatus: DeliveryChallanStatus;
  invoiceId: string;
}

/**
 * The Delivery Challan Detail page's Items section - list, add, edit and
 * delete for one challan's line items, mirroring
 * `PurchaseOrderItemTable`'s Dialog-based CRUD-on-a-Detail-page shape
 * exactly. Add/Edit are plain shadcn `Dialog`s hosting the shared
 * `DeliveryChallanItemForm`, not a routed page. Delete reuses the shared
 * `DeleteConfirmationDialog`.
 *
 * Add/Edit/Delete are only ever offered while `deliveryChallanStatus ===
 * "draft"` - the backend rejects every item mutation with 409
 * `DELIVERY_CHALLAN_NOT_DRAFT` otherwise. Listing remains visible regardless
 * of status, matching the backend's own "allowed regardless of challan
 * status" list behavior.
 */
export function DeliveryChallanItemTable({
  deliveryChallanId,
  deliveryChallanStatus,
  invoiceId,
}: DeliveryChallanItemTableProps) {
  const { hasPermission } = usePermissions();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pendingEditId, setPendingEditId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<DeliveryChallanItemRow | null>(null);

  const itemsQuery = useDeliveryChallanItems(deliveryChallanId);
  const { summaries } = useInvoiceDeliverySummary(invoiceId);
  const createItem = useCreateDeliveryChallanItem();
  const updateItem = useUpdateDeliveryChallanItem();
  const deleteItem = useDeleteDeliveryChallanItem();

  const items = useMemo(() => itemsQuery.data ?? [], [itemsQuery.data]);
  const rows = useMemo(() => buildDeliveryChallanItemRows(items, summaries), [items, summaries]);
  const apiError = itemsQuery.isError ? normalizeApiError(itemsQuery.error) : null;
  const isDraft = deliveryChallanStatus === "draft";
  const canAdd = isDraft && hasPermission("delivery_challan:create");
  const pendingEditRow = rows.find((row) => row.item.id === pendingEditId);

  const rowActionsFor = useDeliveryChallanItemRowActions(
    (row) => setPendingEditId(row.item.id),
    (row) => setPendingDelete(row)
  );
  const columns = useMemo(
    () => getDeliveryChallanItemColumns(isDraft ? rowActionsFor : () => []),
    [isDraft, rowActionsFor]
  );
  const table = useDataTable({ data: rows, columns });

  async function handleCreateSubmit(values: DeliveryChallanItemFormValues) {
    await createItem.mutateAsync({
      deliveryChallanId,
      payload: toDeliveryChallanItemRequestPayload(values),
    });
    toastSuccess("Item added.");
    setIsCreateOpen(false);
  }

  async function handleEditSubmit(values: DeliveryChallanItemFormValues) {
    if (!pendingEditId) return;
    await updateItem.mutateAsync({
      deliveryChallanId,
      itemId: pendingEditId,
      payload: toDeliveryChallanItemUpdatePayload(values),
    });
    toastSuccess("Item updated.");
    setPendingEditId(null);
  }

  return (
    <ContentSection
      title="Delivery Challan Items"
      actions={
        canAdd ? (
          <Button size="sm" onClick={() => setIsCreateOpen(true)}>
            <Plus aria-hidden />
            Add Item
          </Button>
        ) : undefined
      }
    >
      <DataTable
        table={table}
        isLoading={itemsQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load delivery challan items",
                description: apiError.message,
                onRetry: () => itemsQuery.refetch(),
              }
            : null
        }
        isEmpty={!itemsQuery.isLoading && !apiError && rows.length === 0}
        emptyState={
          <DataTableEmpty
            title="No items yet"
            description="Line items on this delivery challan will appear here."
          />
        }
        stickyActionColumn
        aria-label="Delivery challan items"
      />

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Item</DialogTitle>
          </DialogHeader>
          <DeliveryChallanItemForm
            invoiceId={invoiceId}
            onSubmit={handleCreateSubmit}
            onCancel={() => setIsCreateOpen(false)}
            submitLabel="Add Item"
          />
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(pendingEditId)} onOpenChange={(open) => !open && setPendingEditId(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Item</DialogTitle>
          </DialogHeader>
          {pendingEditRow && (
            <DeliveryChallanItemForm
              invoiceId={invoiceId}
              defaultValues={toDeliveryChallanItemFormValues(pendingEditRow.item)}
              editingOwnQuantity={pendingEditRow.item.quantity}
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
          entityName={pendingDelete.description}
          entityLabel="item"
          isLoading={deleteItem.isPending}
          onConfirm={() =>
            deleteItem.mutate(
              { deliveryChallanId, itemId: pendingDelete.item.id },
              { onSuccess: () => setPendingDelete(null) }
            )
          }
        />
      )}
    </ContentSection>
  );
}
