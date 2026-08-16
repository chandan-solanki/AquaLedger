"use client";

import { Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { ContentSection } from "@/components/layout/content-section";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getPurchaseBillItemColumns } from "@/features/purchase-bills/components/purchase-bill-item-columns";
import { PurchaseBillItemForm } from "@/features/purchase-bills/components/purchase-bill-item-form";
import { usePurchaseBillItemRowActions } from "@/features/purchase-bills/components/purchase-bill-item-row-actions";
import { useCreatePurchaseBillItem } from "@/features/purchase-bills/hooks/use-create-purchase-bill-item";
import { useDeletePurchaseBillItem } from "@/features/purchase-bills/hooks/use-delete-purchase-bill-item";
import { usePurchaseBillItem } from "@/features/purchase-bills/hooks/use-purchase-bill-item";
import { usePurchaseBillItems } from "@/features/purchase-bills/hooks/use-purchase-bill-items";
import { useUpdatePurchaseBillItem } from "@/features/purchase-bills/hooks/use-update-purchase-bill-item";
import {
  toPurchaseBillItemFormValues,
  toPurchaseBillItemRequestPayload,
  toPurchaseBillItemUpdatePayload,
  type PurchaseBillItemFormValues,
} from "@/features/purchase-bills/schemas/purchase-bill-item-form-schema";
import type { PurchaseBillStatus } from "@/features/purchase-bills/types/purchase-bill";
import type { PurchaseBillItem } from "@/features/purchase-bills/types/purchase-bill-item";
import { toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface PurchaseBillItemTableProps {
  purchaseBillId: string;
  purchaseBillStatus: PurchaseBillStatus;
  /** The parent bill's own linked purchase order (Sprint 12 Session 12), if any - passed through to `PurchaseBillItemForm` for its optional "Purchase Order Item" selector. */
  purchaseOrderId: string | null;
}

/**
 * The Purchase Bill Detail page's Items section - list, add, edit and
 * delete for one bill's line items, mirroring `InvoiceItemTable`'s Dialog-
 * based CRUD-on-a-Detail-page shape exactly. Add/Edit are plain shadcn
 * `Dialog`s hosting the shared `PurchaseBillItemForm`, not a routed page.
 * Delete reuses the shared `DeleteConfirmationDialog`.
 *
 * Add/Edit/Delete are only ever offered while `purchaseBillStatus ===
 * "draft"` - the backend rejects every item mutation with 409
 * `PURCHASE_BILL_NOT_DRAFT` otherwise (app/modules/purchase/service.py's
 * `_ensure_draft`), matching `03_INFORMATION_ARCHITECTURE.md` §13's "render
 * only the currently valid action" rule. Listing remains visible regardless
 * of status, matching the backend's own "allowed regardless of bill status"
 * list behavior.
 */
export function PurchaseBillItemTable({
  purchaseBillId,
  purchaseBillStatus,
  purchaseOrderId,
}: PurchaseBillItemTableProps) {
  const { hasPermission } = usePermissions();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pendingEditId, setPendingEditId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PurchaseBillItem | null>(null);

  const itemsQuery = usePurchaseBillItems(purchaseBillId);
  const editItemQuery = usePurchaseBillItem(purchaseBillId, pendingEditId ?? undefined);
  const createItem = useCreatePurchaseBillItem();
  const updateItem = useUpdatePurchaseBillItem();
  const deleteItem = useDeletePurchaseBillItem();

  const items = useMemo(() => itemsQuery.data ?? [], [itemsQuery.data]);
  const apiError = itemsQuery.isError ? normalizeApiError(itemsQuery.error) : null;
  const isDraft = purchaseBillStatus === "draft";
  const canAdd = isDraft && hasPermission("purchase:create");

  const rowActionsFor = usePurchaseBillItemRowActions(
    (item) => setPendingEditId(item.id),
    (item) => setPendingDelete(item)
  );
  const columns = useMemo(
    () => getPurchaseBillItemColumns(isDraft ? rowActionsFor : () => []),
    [isDraft, rowActionsFor]
  );
  const table = useDataTable({ data: items, columns });

  async function handleCreateSubmit(values: PurchaseBillItemFormValues) {
    await createItem.mutateAsync({
      purchaseBillId,
      payload: toPurchaseBillItemRequestPayload(values),
    });
    toastSuccess("Item added.");
    setIsCreateOpen(false);
  }

  async function handleEditSubmit(values: PurchaseBillItemFormValues) {
    if (!pendingEditId) return;
    await updateItem.mutateAsync({
      purchaseBillId,
      itemId: pendingEditId,
      payload: toPurchaseBillItemUpdatePayload(values),
    });
    toastSuccess("Item updated.");
    setPendingEditId(null);
  }

  return (
    <ContentSection
      title="Purchase Bill Items"
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
                title: "Failed to load purchase bill items",
                description: apiError.message,
                onRetry: () => itemsQuery.refetch(),
              }
            : null
        }
        isEmpty={!itemsQuery.isLoading && !apiError && items.length === 0}
        emptyState={
          <DataTableEmpty title="No items yet" description="Line items on this purchase bill will appear here." />
        }
        stickyActionColumn
        aria-label="Purchase bill items"
      />

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Item</DialogTitle>
          </DialogHeader>
          <PurchaseBillItemForm
            onSubmit={handleCreateSubmit}
            onCancel={() => setIsCreateOpen(false)}
            submitLabel="Add Item"
            purchaseOrderId={purchaseOrderId}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(pendingEditId)} onOpenChange={(open) => !open && setPendingEditId(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Item</DialogTitle>
          </DialogHeader>
          {editItemQuery.data && (
            <PurchaseBillItemForm
              defaultValues={toPurchaseBillItemFormValues(editItemQuery.data)}
              onSubmit={handleEditSubmit}
              onCancel={() => setPendingEditId(null)}
              submitLabel="Save Changes"
              purchaseOrderId={purchaseOrderId}
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
              { purchaseBillId, itemId: pendingDelete.id },
              { onSuccess: () => setPendingDelete(null) }
            )
          }
        />
      )}
    </ContentSection>
  );
}
