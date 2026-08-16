"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import type { InvoiceItemDeliverySummary } from "@/features/delivery-challans/hooks/use-invoice-delivery-summary";
import type { DeliveryChallanItem } from "@/features/delivery-challans/types/delivery-challan-item";
import { formatQuantity } from "@/utils/format-number";

export interface DeliveryChallanItemRow {
  item: DeliveryChallanItem;
  /** The invoice item this line delivers against - undefined only while the invoice's own items are still loading. */
  description: string;
  invoicedQuantity: string | undefined;
  /** Total delivered against the same invoice item across every non-cancelled challan, minus this line's own quantity (see `use-invoice-delivery-summary.ts`). */
  deliveredBefore: number | undefined;
  /** `invoicedQuantity - (deliveredBefore + this line's own quantity)` - what remains once this delivery is accounted for. */
  remainingAfter: number | undefined;
}

export function buildDeliveryChallanItemRows(
  items: DeliveryChallanItem[],
  summaries: InvoiceItemDeliverySummary[]
): DeliveryChallanItemRow[] {
  const summaryByInvoiceItemId = new Map(summaries.map((summary) => [summary.invoiceItem.id, summary]));

  return items.map((item) => {
    const summary = summaryByInvoiceItemId.get(item.invoiceItemId);
    return {
      item,
      description: summary?.invoiceItem.description ?? "Item",
      invoicedQuantity: summary?.invoiceItem.quantity,
      deliveredBefore: summary ? summary.deliveredQuantity - Number(item.quantity) : undefined,
      remainingAfter: summary?.remainingQuantity,
    };
  });
}

/**
 * The Delivery Challan Items sub-table's column set, per this session's own
 * Phase 12: Description/Fish, Invoice Quantity, Delivered Before, This
 * Challan Quantity, Remaining After Delivery, Unit, Actions. Every quantity
 * column beyond the line's own `quantity`/`unit` (both straight from
 * `DeliveryChallanItemResponse`) is a UX-only figure computed by
 * `use-invoice-delivery-summary.ts` - never authoritative, the backend
 * remains the actual authority on every write. No sorting - this table has
 * no sort UI, mirroring `getPurchaseOrderItemColumns`.
 */
export function getDeliveryChallanItemColumns(
  rowActions: (row: DeliveryChallanItemRow) => DataTableAction<DeliveryChallanItemRow>[]
): DataTableColumn<DeliveryChallanItemRow>[] {
  return [
    {
      id: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Description" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.description}</span>,
    },
    {
      id: "invoicedQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoiced" />,
      enableSorting: false,
      cell: ({ row }) =>
        row.original.invoicedQuantity !== undefined
          ? `${formatQuantity(row.original.invoicedQuantity)} ${row.original.item.unit}`
          : "—",
      meta: { align: "right" },
    },
    {
      id: "deliveredBefore",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Delivered Before" />,
      enableSorting: false,
      cell: ({ row }) =>
        row.original.deliveredBefore !== undefined
          ? `${formatQuantity(row.original.deliveredBefore)} ${row.original.item.unit}`
          : "—",
      meta: { align: "right" },
    },
    {
      id: "thisChallanQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="This Challan" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-medium">
          {formatQuantity(row.original.item.quantity)} {row.original.item.unit}
        </span>
      ),
      meta: { align: "right" },
    },
    {
      id: "remainingAfter",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Remaining After" />,
      enableSorting: false,
      cell: ({ row }) =>
        row.original.remainingAfter !== undefined
          ? `${formatQuantity(row.original.remainingAfter)} ${row.original.item.unit}`
          : "—",
      meta: { align: "right" },
    },
    createRowActionsColumn<DeliveryChallanItemRow>(rowActions),
  ];
}
