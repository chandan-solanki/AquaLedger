"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { DataTable, DataTableColumnHeader, DataTableEmpty, useDataTable } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripCatchInvoiceUsageDialog } from "@/features/invoices/components/trip-catch-invoice-usage-dialog";
import type { TripCatchInvoiceUsage } from "@/features/invoices/types/trip-catch-invoice-usage";
import type { FishStockContributingCatch } from "@/features/fish-stock/types/fish-stock";
import { formatQuantity } from "@/utils/format-number";
import { formatDate } from "@/utils/format-date";

interface FishStockContributingCatchesTableProps {
  catches: FishStockContributingCatch[];
  isLoading: boolean;
  /** Sprint 15 Session 7 - keyed by tripCatchId; absent means zero usage. */
  usageByTripCatchId?: Map<string, TripCatchInvoiceUsage>;
  isUsageLoading?: boolean;
  unitLabel: string;
}

/**
 * Sprint 15 Session 7: "Invoice Usage" cell - visually subtle (plain muted
 * text, no badge/highlight that could read as reserved stock), but
 * discoverable (clickable when the count is non-zero and the caller has
 * `invoice:view`). A missing/zero usage entry renders a dash, never "0
 * invoices" - matching the rest of this table's quiet, no-noise style.
 *
 * Deliberately never labeled "Reserved" or "Committed Stock" (TASKS.md
 * Sprint 15 Session 7 §3) - draft invoices only ever reference a catch, they
 * never reduce its available_quantity; only an issued invoice does that
 * (already reflected in the Sold column). `draftQuantity`/`consumedQuantity`
 * are shown only when non-zero, so a catch referenced only by drafts (or
 * only consumed) doesn't show a redundant "0.000" line.
 */
function InvoiceUsageCell({
  tripCatchId,
  usage,
  isLoading,
  unitLabel,
}: {
  tripCatchId: string;
  usage: TripCatchInvoiceUsage | undefined;
  isLoading: boolean;
  unitLabel: string;
}) {
  const { hasPermission } = usePermissions();
  const [open, setOpen] = useState(false);
  const canViewInvoices = hasPermission("invoice:view");

  if (isLoading) {
    return <span className="text-muted-foreground">…</span>;
  }
  if (!usage || usage.invoiceCount === 0) {
    return <span className="text-muted-foreground">—</span>;
  }

  const countLabel = `${usage.invoiceCount} invoice${usage.invoiceCount === 1 ? "" : "s"}`;
  const hasDraft = Number(usage.draftQuantity) > 0;
  const hasConsumed = Number(usage.consumedQuantity) > 0;
  const detailLabel =
    hasDraft || hasConsumed
      ? [
          hasDraft && `${formatQuantity(usage.draftQuantity)} ${unitLabel} draft`,
          hasConsumed && `${formatQuantity(usage.consumedQuantity)} ${unitLabel} consumed`,
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
        aria-label={`View invoices referencing this catch (${countLabel})`}
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
        />
      )}
    </>
  );
}

function getColumns(
  canCreateInvoice: boolean,
  usageByTripCatchId: Map<string, TripCatchInvoiceUsage> | undefined,
  isUsageLoading: boolean,
  unitLabel: string
): DataTableColumn<FishStockContributingCatch>[] {
  return [
    {
      accessorKey: "tripNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.tripNumber}</span>,
    },
    {
      accessorKey: "landingDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Landing Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.landingDate),
    },
    {
      accessorKey: "quantityCaught",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Caught" />,
      enableSorting: false,
      cell: ({ row }) => formatQuantity(row.original.quantityCaught),
      meta: { align: "right" },
    },
    {
      accessorKey: "soldQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Sold" />,
      enableSorting: false,
      cell: ({ row }) => formatQuantity(row.original.soldQuantity),
      meta: { align: "right" },
    },
    {
      accessorKey: "availableQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Available" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-semibold text-primary tabular-nums">
          {formatQuantity(row.original.availableQuantity)}
        </span>
      ),
      meta: { align: "right" },
    },
    {
      accessorKey: "wasteQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Waste" />,
      enableSorting: false,
      cell: ({ row }) => formatQuantity(row.original.wasteQuantity),
      meta: { align: "right" },
    },
    {
      id: "invoiceUsage",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Usage" />,
      enableSorting: false,
      cell: ({ row }) => (
        <InvoiceUsageCell
          tripCatchId={row.original.tripCatchId}
          usage={usageByTripCatchId?.get(row.original.tripCatchId)}
          isLoading={isUsageLoading}
          unitLabel={unitLabel}
        />
      ),
    },
    ...(canCreateInvoice
      ? ([
          {
            id: "actions",
            header: "",
            enableSorting: false,
            cell: ({ row }) =>
              Number(row.original.availableQuantity) > 0 ? (
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/invoices/new?tripCatchId=${row.original.tripCatchId}`}>Create Invoice</Link>
                </Button>
              ) : null,
            meta: { align: "right" },
          },
        ] satisfies DataTableColumn<FishStockContributingCatch>[])
      : []),
  ];
}

/**
 * The Fish Stock detail page's "Contributing Catches" section - every
 * `trip_catches` row the backend's GET /fish-stock/{fish_id} already
 * returned, rendered as-is (no separate fetch, no pagination: the API
 * returns the full bounded list for one fish in one response, the same
 * "small and bounded" reasoning `TripCatchTable` uses for a single trip's
 * catches). Only fields the API actually returns are shown - no landing
 * port, no remarks, no grade, since FishStockContributingCatch
 * (app/modules/trip_catches/schemas.py) doesn't carry them.
 *
 * Sprint 15 Session 4: each row with `available_quantity > 0` gets its own
 * "Create Invoice" link straight to `/invoices/new?tripCatchId=<id>` - the
 * specific catch, not just the fish, since stock is maintained at the
 * TripCatch level (a Pomfret catch from Trip A and one from Trip B are
 * never fungible). Depleted catches (`available_quantity === 0`) render no
 * action, matching the same "don't encourage a doomed submission" posture
 * `TripCatchSelectorField` takes for zero-stock options. Gated on
 * `invoice:create` only - no new permission.
 *
 * Sprint 15 Session 7: an "Invoice Usage" column shows how many invoices
 * reference each catch (`usageByTripCatchId`, from the batched
 * `GET /invoices/trip-catches/usage-summary`, Session 7) - visibility only,
 * gated on `fish:view` (this whole page's own gate), never `invoice:view`.
 * Only the per-catch drill-down (which surfaces real invoice numbers/
 * companies) requires `invoice:view` - see `InvoiceUsageCell`.
 */
export function FishStockContributingCatchesTable({
  catches,
  isLoading,
  usageByTripCatchId,
  isUsageLoading = false,
  unitLabel,
}: FishStockContributingCatchesTableProps) {
  const { hasPermission } = usePermissions();
  const canCreateInvoice = hasPermission("invoice:create");
  const columns = useMemo(
    () => getColumns(canCreateInvoice, usageByTripCatchId, isUsageLoading, unitLabel),
    [canCreateInvoice, usageByTripCatchId, isUsageLoading, unitLabel]
  );
  const table = useDataTable({ data: catches, columns });

  return (
    <DataTable
      table={table}
      isLoading={isLoading}
      isEmpty={!isLoading && catches.length === 0}
      emptyState={
        <DataTableEmpty
          title="No contributing catches"
          description="Trip catches recorded for this fish will appear here."
        />
      }
      aria-label="Contributing catches"
    />
  );
}
