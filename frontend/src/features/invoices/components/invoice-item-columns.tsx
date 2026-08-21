"use client";

import { useState } from "react";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Fish } from "@/features/fish";
import { TripCatchInvoiceUsageDialog } from "@/features/invoices/components/trip-catch-invoice-usage-dialog";
import type { InvoiceItem } from "@/features/invoices/types/invoice-item";
import type { TripCatchOtherInvoiceUsage } from "@/features/invoices/types/trip-catch-other-invoice-usage";
import { formatCurrency } from "@/utils/format-currency";
import { formatQuantity, formatRate } from "@/utils/format-number";

/**
 * Sprint 15 Session 8: "Other Invoice Usage" cell - proactive visibility on
 * the Invoice Detail page's own item table, mirroring Session 7's Fish
 * Stock `InvoiceUsageCell` (subtle muted text, clickable only when non-zero
 * and the caller has `invoice:view`), but always phrased relative to "other
 * than the invoice I'm looking at" - "2 other invoices," never "2
 * invoices" (which would misleadingly include this invoice's own item).
 * Never labeled "Reserved"/"Committed Stock" - draft invoices only ever
 * reference a catch, they never reduce its available_quantity.
 */
function OtherInvoiceUsageCell({
  invoiceId,
  tripCatchId,
  usage,
  isLoading,
  unitLabel,
}: {
  invoiceId: string;
  tripCatchId: string | null;
  usage: TripCatchOtherInvoiceUsage | undefined;
  isLoading: boolean;
  unitLabel: string;
}) {
  const { hasPermission } = usePermissions();
  const [open, setOpen] = useState(false);
  const canViewInvoices = hasPermission("invoice:view");

  if (!tripCatchId) {
    return <span className="text-muted-foreground">—</span>;
  }
  if (isLoading) {
    return <span className="text-muted-foreground">…</span>;
  }
  if (!usage || usage.otherInvoiceCount === 0) {
    return <span className="text-muted-foreground">—</span>;
  }

  const countLabel = `${usage.otherInvoiceCount} other invoice${usage.otherInvoiceCount === 1 ? "" : "s"}`;
  const hasDraft = Number(usage.otherDraftQuantity) > 0;
  const hasConsumed = Number(usage.otherConsumedQuantity) > 0;
  const detailLabel =
    hasDraft || hasConsumed
      ? [
          hasDraft && `${formatQuantity(usage.otherDraftQuantity)} ${unitLabel} draft`,
          hasConsumed && `${formatQuantity(usage.otherConsumedQuantity)} ${unitLabel} consumed`,
        ]
          .filter(Boolean)
          .join(" · ")
      : null;

  const content = (
    <div className="text-sm">
      <div>{countLabel}</div>
      {detailLabel && <div className="text-xs text-muted-foreground">{detailLabel}</div>}
    </div>
  );

  if (!canViewInvoices) {
    return content;
  }

  return (
    <>
      <button
        type="button"
        className="text-left hover:underline"
        aria-label={`View other invoices referencing this catch (${countLabel})`}
        onClick={() => setOpen(true)}
      >
        {content}
      </button>
      {open && (
        <TripCatchInvoiceUsageDialog
          open={open}
          onOpenChange={setOpen}
          tripCatchId={tripCatchId}
          unitLabel={unitLabel}
          currentInvoiceId={invoiceId}
        />
      )}
    </>
  );
}

/**
 * The Invoice Items sub-table's column set: Fish, Description, Quantity,
 * Rate, Discount %, Taxable Amount, Tax %, Tax Amount, Line Total, Other
 * Invoice Usage, Actions - every field `InvoiceItemResponse` carries
 * (app/modules/invoices/schemas.py) except id/tenant_id/invoice_id/
 * line_number (implicit - line_number is purely a server-assigned ordering
 * key, not a viewing concern), and created_at/updated_at.
 * `discountAmount`/`taxableAmount`/`taxAmount`/`lineTotal` are rendered
 * straight from the server's response - never recalculated here, per "the
 * backend owns financial calculations." No sorting - this table has no sort
 * UI (see `InvoiceItemTable`), mirroring `getTripExpenseColumns`. `fishById`
 * resolves each row's `fish_id` to a display name - `InvoiceItemResponse`
 * carries no nested fish object.
 *
 * Sprint 15 Session 8: `usageByTripCatchId`/`isUsageLoading` (from the
 * page-level `useInvoiceTripCatchConflicts`, one call for the whole table)
 * feed the new Other Invoice Usage column - `trip_catch_id` was previously
 * unused here (an entry-time sourcing reference, not a display column) but
 * is now needed to key that lookup and open the correct catch's dialog.
 */
export function getInvoiceItemColumns(
  rowActions: (item: InvoiceItem) => DataTableAction<InvoiceItem>[],
  fishById: Map<string, Fish>,
  invoiceId: string,
  usageByTripCatchId?: Map<string, TripCatchOtherInvoiceUsage>,
  isUsageLoading = false
): DataTableColumn<InvoiceItem>[] {
  return [
    {
      accessorKey: "fishId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Fish" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{fishById.get(row.original.fishId)?.name ?? "—"}</span>,
    },
    {
      accessorKey: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Description" />,
      enableSorting: false,
      cell: ({ row }) => row.original.description ?? "—",
    },
    {
      accessorKey: "quantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Quantity" />,
      enableSorting: false,
      cell: ({ row }) => `${formatQuantity(row.original.quantity)} ${row.original.unit}`,
      meta: { align: "right" },
    },
    {
      accessorKey: "rate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Rate" />,
      enableSorting: false,
      cell: ({ row }) => formatRate(row.original.rate),
      meta: { align: "right" },
    },
    {
      accessorKey: "discountPercent",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Discount %" />,
      enableSorting: false,
      cell: ({ row }) => `${row.original.discountPercent}%`,
      meta: { align: "right" },
    },
    {
      accessorKey: "taxableAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Taxable Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.taxableAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "taxRate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Tax %" />,
      enableSorting: false,
      cell: ({ row }) => `${row.original.taxRate}%`,
      meta: { align: "right" },
    },
    {
      accessorKey: "taxAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Tax Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.taxAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "lineTotal",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Line Total" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.lineTotal)}</span>,
      meta: { align: "right" },
    },
    {
      id: "otherInvoiceUsage",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Other Invoice Usage" />,
      enableSorting: false,
      cell: ({ row }) => (
        <OtherInvoiceUsageCell
          invoiceId={invoiceId}
          tripCatchId={row.original.tripCatchId}
          usage={row.original.tripCatchId ? usageByTripCatchId?.get(row.original.tripCatchId) : undefined}
          isLoading={isUsageLoading}
          unitLabel={row.original.unit}
        />
      ),
    },
    createRowActionsColumn<InvoiceItem>(rowActions),
  ];
}
