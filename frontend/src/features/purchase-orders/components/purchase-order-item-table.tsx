"use client";

import { Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { ContentSection } from "@/components/layout/content-section";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getPurchaseOrderItemColumns } from "@/features/purchase-orders/components/purchase-order-item-columns";
import { PurchaseOrderItemForm } from "@/features/purchase-orders/components/purchase-order-item-form";
import { usePurchaseOrderItemRowActions } from "@/features/purchase-orders/components/purchase-order-item-row-actions";
import { useCreatePurchaseOrderItem } from "@/features/purchase-orders/hooks/use-create-purchase-order-item";
import { useDeletePurchaseOrderItem } from "@/features/purchase-orders/hooks/use-delete-purchase-order-item";
import { usePurchaseOrderItem } from "@/features/purchase-orders/hooks/use-purchase-order-item";
import { usePurchaseOrderItems } from "@/features/purchase-orders/hooks/use-purchase-order-items";
import { useUpdatePurchaseOrderItem } from "@/features/purchase-orders/hooks/use-update-purchase-order-item";
import {
  toPurchaseOrderItemFormValues,
  toPurchaseOrderItemRequestPayload,
  toPurchaseOrderItemUpdatePayload,
  type PurchaseOrderItemFormValues,
} from "@/features/purchase-orders/schemas/purchase-order-item-form-schema";
import type { PurchaseOrderStatus } from "@/features/purchase-orders/types/purchase-order";
import type { PurchaseOrderItem } from "@/features/purchase-orders/types/purchase-order-item";
import { toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface PurchaseOrderItemTableProps {
  purchaseOrderId: string;
  purchaseOrderStatus: PurchaseOrderStatus;
}

/**
 * The Purchase Order Detail page's Items section - list, add, edit and
 * delete for one order's line items, mirroring `PurchaseBillItemTable`'s
 * Dialog-based CRUD-on-a-Detail-page shape exactly. Add/Edit are plain
 * shadcn `Dialog`s hosting the shared `PurchaseOrderItemForm`, not a routed
 * page. Delete reuses the shared `DeleteConfirmationDialog`.
 *
 * Add/Edit/Delete are only ever offered while `purchaseOrderStatus ===
 * "draft"` - the backend rejects every item mutation with 409
 * `PURCHASE_ORDER_NOT_DRAFT` otherwise. Listing remains visible regardless
 * of status, matching the backend's own "allowed regardless of order
 * status" list behavior.
 */
export function PurchaseOrderItemTable({ purchaseOrderId, purchaseOrderStatus }: PurchaseOrderItemTableProps) {
  const { hasPermission } = usePermissions();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pendingEditId, setPendingEditId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PurchaseOrderItem | null>(null);

  const itemsQuery = usePurchaseOrderItems(purchaseOrderId);
  const editItemQuery = usePurchaseOrderItem(purchaseOrderId, pendingEditId ?? undefined);
  const createItem = useCreatePurchaseOrderItem();
  const updateItem = useUpdatePurchaseOrderItem();
  const deleteItem = useDeletePurchaseOrderItem();

  const items = useMemo(() => itemsQuery.data ?? [], [itemsQuery.data]);
  const apiError = itemsQuery.isError ? normalizeApiError(itemsQuery.error) : null;
  const isDraft = purchaseOrderStatus === "draft";
  const canAdd = isDraft && hasPermission("purchase_order:create");

  const rowActionsFor = usePurchaseOrderItemRowActions(
    (item) => setPendingEditId(item.id),
    (item) => setPendingDelete(item)
  );
  const columns = useMemo(
    () => getPurchaseOrderItemColumns(isDraft ? rowActionsFor : () => []),
    [isDraft, rowActionsFor]
  );
  const table = useDataTable({ data: items, columns });

  async function handleCreateSubmit(values: PurchaseOrderItemFormValues) {
    await createItem.mutateAsync({
      purchaseOrderId,
      payload: toPurchaseOrderItemRequestPayload(values),
    });
    toastSuccess("Item added.");
    setIsCreateOpen(false);
  }

  async function handleEditSubmit(values: PurchaseOrderItemFormValues) {
    if (!pendingEditId) return;
    await updateItem.mutateAsync({
      purchaseOrderId,
      itemId: pendingEditId,
      payload: toPurchaseOrderItemUpdatePayload(values),
    });
    toastSuccess("Item updated.");
    setPendingEditId(null);
  }

  return (
    <ContentSection
      title="Purchase Order Items"
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
                title: "Failed to load purchase order items",
                description: apiError.message,
                onRetry: () => itemsQuery.refetch(),
              }
            : null
        }
        isEmpty={!itemsQuery.isLoading && !apiError && items.length === 0}
        emptyState={
          <DataTableEmpty title="No items yet" description="Line items on this purchase order will appear here." />
        }
        stickyActionColumn
        aria-label="Purchase order items"
      />

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Item</DialogTitle>
          </DialogHeader>
          <PurchaseOrderItemForm
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
          {editItemQuery.data && (
            <PurchaseOrderItemForm
              defaultValues={toPurchaseOrderItemFormValues(editItemQuery.data)}
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
          entityName={pendingDelete.description ?? "this item"}
          entityLabel="item"
          isLoading={deleteItem.isPending}
          onConfirm={() =>
            deleteItem.mutate(
              { purchaseOrderId, itemId: pendingDelete.id },
              { onSuccess: () => setPendingDelete(null) }
            )
          }
        />
      )}
    </ContentSection>
  );
}
