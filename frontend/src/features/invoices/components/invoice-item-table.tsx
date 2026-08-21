"use client";

import { Plus } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { ContentSection } from "@/components/layout/content-section";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { tripCatchService, useFishOptions } from "@/features/trips";
import { getInvoiceItemColumns } from "@/features/invoices/components/invoice-item-columns";
import { InvoiceItemForm } from "@/features/invoices/components/invoice-item-form";
import { useInvoiceItemRowActions } from "@/features/invoices/components/invoice-item-row-actions";
import { useCreateInvoiceItem } from "@/features/invoices/hooks/use-create-invoice-item";
import { useDeleteInvoiceItem } from "@/features/invoices/hooks/use-delete-invoice-item";
import { useInvoiceItem } from "@/features/invoices/hooks/use-invoice-item";
import { useInvoiceItems } from "@/features/invoices/hooks/use-invoice-items";
import { useInvoiceTripCatchConflicts } from "@/features/invoices/hooks/use-invoice-trip-catch-conflicts";
import { useUpdateInvoiceItem } from "@/features/invoices/hooks/use-update-invoice-item";
import {
  toInvoiceItemFormValues,
  toInvoiceItemRequestPayload,
  toInvoiceItemUpdatePayload,
  type InvoiceItemFormValues,
} from "@/features/invoices/schemas/invoice-item-form-schema";
import type { InvoiceStatus } from "@/features/invoices/types/invoice";
import type { InvoiceItem } from "@/features/invoices/types/invoice-item";
import { toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface InvoiceItemTableProps {
  invoiceId: string;
  invoiceStatus: InvoiceStatus;
}

/**
 * The Invoice Detail page's Items section - list, add, edit and delete for
 * one invoice's line items (Sprint 7 Session 3, see TASKS.md). Add/Edit are
 * plain shadcn `Dialog`s hosting the shared `InvoiceItemForm`, not separate
 * routed pages - unlike Trip Catch's `/trips/{id}/catches/new`, this
 * session's Routes scope is `/invoices/[id]` only, so item CRUD stays
 * inline on this same page. Delete reuses the shared
 * `DeleteConfirmationDialog`, mirroring `TripCatchTable`.
 *
 * Add/Edit/Delete are only ever offered while `invoiceStatus === "draft"` -
 * the backend rejects every item mutation with 409 `INVOICE_NOT_DRAFT`
 * otherwise (app/modules/invoices/service.py's `_ensure_draft`), matching
 * `03_INFORMATION_ARCHITECTURE.md` §13's "render only the currently valid
 * action" rule. Listing remains visible regardless of status, matching the
 * backend's own "allowed regardless of invoice status" list behavior.
 *
 * Owns the whole Items section (heading, Add button, table, dialogs) rather
 * than splitting the heading/action into the parent Detail page the way
 * `TripDetailPage`/`TripCatchTable` do - Trip Catch's "Add" is a plain
 * `<Link>` to a route, but this section's "Add" opens a Dialog whose state
 * has to live somewhere, and keeping it here avoids lifting dialog-open
 * state into the Detail page for no benefit.
 *
 * Sprint 15 Session 4: an `?openItem=<tripCatchId>` query param (set by
 * `InvoiceCreatePage` after creating an invoice from the Fish Stock detail
 * page's "Create Invoice" action) auto-opens the Add Item dialog with that
 * catch pre-selected, then the param is stripped via `router.replace` so a
 * refresh or a later manual "Add Item" click never re-triggers it.
 *
 * Sprint 15 Session 8: one page-level `useInvoiceTripCatchConflicts` fetch
 * feeds every row's "Other Invoice Usage" cell (`getInvoiceItemColumns`) -
 * never one request per item, regardless of how many items this invoice
 * has.
 */
export function InvoiceItemTable({ invoiceId, invoiceStatus }: InvoiceItemTableProps) {
  const { hasPermission } = usePermissions();
  const router = useRouter();
  const searchParams = useSearchParams();
  const openItemTripCatchId = searchParams.get("openItem");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createDefaultValues, setCreateDefaultValues] = useState<InvoiceItemFormValues | undefined>();
  const [pendingEditId, setPendingEditId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<InvoiceItem | null>(null);
  const hasConsumedOpenItemParam = useRef(false);

  const itemsQuery = useInvoiceItems(invoiceId);
  const editItemQuery = useInvoiceItem(invoiceId, pendingEditId ?? undefined);
  const fishOptions = useFishOptions();
  const createInvoiceItem = useCreateInvoiceItem();
  const updateInvoiceItem = useUpdateInvoiceItem();
  const deleteInvoiceItem = useDeleteInvoiceItem();
  const conflictsQuery = useInvoiceTripCatchConflicts(invoiceId);

  const prefillCatchQuery = useQuery({
    queryKey: ["trip-catches", "detail", openItemTripCatchId],
    queryFn: () => tripCatchService.getTripCatch(openItemTripCatchId!),
    enabled: Boolean(openItemTripCatchId),
    retry: false,
  });

  useEffect(() => {
    if (!openItemTripCatchId || hasConsumedOpenItemParam.current) return;
    if (prefillCatchQuery.isError) {
      hasConsumedOpenItemParam.current = true;
      router.replace(`/invoices/${invoiceId}`);
      return;
    }
    const catchDetail = prefillCatchQuery.data;
    if (!catchDetail) return;
    const fish = fishOptions.fishById.get(catchDetail.fishId);
    if (!fish) return;

    hasConsumedOpenItemParam.current = true;
    setCreateDefaultValues({
      trip_catch_id: catchDetail.id,
      fish_id: catchDetail.fishId,
      description: "",
      quantity: "",
      unit: fish.unit,
      rate: "",
      discount_percent: "",
      tax_rate: "",
    });
    setIsCreateOpen(true);
    router.replace(`/invoices/${invoiceId}`);
  }, [openItemTripCatchId, prefillCatchQuery.data, prefillCatchQuery.isError, fishOptions.fishById, invoiceId, router]);

  const items = useMemo(() => itemsQuery.data ?? [], [itemsQuery.data]);
  const apiError = itemsQuery.isError ? normalizeApiError(itemsQuery.error) : null;
  const isDraft = invoiceStatus === "draft";
  const canAdd = isDraft && hasPermission("invoice:create");

  // Sprint 15 Session 8: undefined (not an empty Map) whenever the fetch
  // hasn't resolved yet or failed - OtherInvoiceUsageCell already renders a
  // loading placeholder or a dash for an undefined map, so a failed summary
  // fetch degrades gracefully instead of crashing this page.
  const usageByTripCatchId = useMemo(() => {
    if (!conflictsQuery.data) return undefined;
    return new Map(conflictsQuery.data.map((usage) => [usage.tripCatchId, usage]));
  }, [conflictsQuery.data]);

  const rowActionsFor = useInvoiceItemRowActions(
    (item) => setPendingEditId(item.id),
    (item) => setPendingDelete(item)
  );
  const columns = useMemo(
    () =>
      getInvoiceItemColumns(
        isDraft ? rowActionsFor : () => [],
        fishOptions.fishById,
        invoiceId,
        usageByTripCatchId,
        conflictsQuery.isLoading
      ),
    [isDraft, rowActionsFor, fishOptions.fishById, invoiceId, usageByTripCatchId, conflictsQuery.isLoading]
  );
  const table = useDataTable({ data: items, columns });

  function closeCreateDialog() {
    setIsCreateOpen(false);
    setCreateDefaultValues(undefined);
  }

  async function handleCreateSubmit(values: InvoiceItemFormValues) {
    await createInvoiceItem.mutateAsync({ invoiceId, payload: toInvoiceItemRequestPayload(values) });
    toastSuccess("Item added.");
    closeCreateDialog();
  }

  async function handleEditSubmit(values: InvoiceItemFormValues) {
    if (!pendingEditId) return;
    await updateInvoiceItem.mutateAsync({
      invoiceId,
      itemId: pendingEditId,
      payload: toInvoiceItemUpdatePayload(values),
    });
    toastSuccess("Item updated.");
    setPendingEditId(null);
  }

  return (
    <ContentSection
      title="Invoice Items"
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
                title: "Failed to load invoice items",
                description: apiError.message,
                onRetry: () => itemsQuery.refetch(),
              }
            : null
        }
        isEmpty={!itemsQuery.isLoading && !apiError && items.length === 0}
        emptyState={<DataTableEmpty title="No items yet" description="Line items you add will appear here." />}
        stickyActionColumn
        aria-label="Invoice items"
      />

      <Dialog open={isCreateOpen} onOpenChange={(open) => !open && closeCreateDialog()}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Item</DialogTitle>
          </DialogHeader>
          <InvoiceItemForm
            invoiceId={invoiceId}
            defaultValues={createDefaultValues}
            onSubmit={handleCreateSubmit}
            onCancel={closeCreateDialog}
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
            <InvoiceItemForm
              invoiceId={invoiceId}
              defaultValues={toInvoiceItemFormValues(editItemQuery.data)}
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
          entityName={fishOptions.fishById.get(pendingDelete.fishId)?.name ?? "this item"}
          entityLabel="invoice item"
          isLoading={deleteInvoiceItem.isPending}
          onConfirm={() =>
            deleteInvoiceItem.mutate(
              { invoiceId, itemId: pendingDelete.id },
              { onSuccess: () => setPendingDelete(null) }
            )
          }
        />
      )}
    </ContentSection>
  );
}
