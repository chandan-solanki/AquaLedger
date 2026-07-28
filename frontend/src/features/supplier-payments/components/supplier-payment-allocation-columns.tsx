"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import type { PurchaseBill } from "@/features/purchase-bills";
import type { SupplierPaymentAllocation } from "@/features/supplier-payments/types/supplier-payment-allocation";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Supplier Payment Allocations sub-table's column set: Purchase Bill
 * Number, Bill Date, Bill Total, Allocated Amount, Bill Balance, Actions -
 * every money/date value rendered straight from the server's own response,
 * never recalculated here, per "the backend owns financial calculations."
 * `SupplierPaymentAllocationResponse` carries only `purchase_bill_id`
 * (app/modules/supplier_payments/schemas.py) - no bill_number/bill_date/
 * total_amount/balance_amount of its own - so `purchaseBillById` resolves
 * each row's `purchase_bill_id` to the referenced bill (fetched via
 * `@/features/purchase-bills`' own `purchaseBillService`, see
 * `supplier-payment-allocation-table.tsx`), mirroring
 * `getPaymentAllocationColumns`. "Bill Balance" is that bill's own
 * current `balance_amount`, exactly as the backend returns it - not a
 * point-in-time "balance before this allocation" snapshot, which the
 * backend does not expose anywhere. No sorting - this table has no sort UI,
 * mirroring `getPaymentAllocationColumns`.
 */
export function getSupplierPaymentAllocationColumns(
  rowActions: (allocation: SupplierPaymentAllocation) => DataTableAction<SupplierPaymentAllocation>[],
  purchaseBillById: Map<string, PurchaseBill>
): DataTableColumn<SupplierPaymentAllocation>[] {
  return [
    {
      accessorKey: "purchaseBillId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Purchase Bill Number" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-medium">
          {purchaseBillById.get(row.original.purchaseBillId)?.billNumber ?? "—"}
        </span>
      ),
    },
    {
      id: "bill_date",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Date" />,
      enableSorting: false,
      cell: ({ row }) => {
        const bill = purchaseBillById.get(row.original.purchaseBillId);
        return bill ? formatDate(bill.billDate) : "—";
      },
    },
    {
      id: "bill_total",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Total" />,
      enableSorting: false,
      cell: ({ row }) => {
        const bill = purchaseBillById.get(row.original.purchaseBillId);
        return bill ? formatCurrency(bill.totalAmount) : "—";
      },
      meta: { align: "right" },
    },
    {
      accessorKey: "allocatedAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Allocated Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.allocatedAmount),
      meta: { align: "right" },
    },
    {
      id: "bill_balance",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Balance" />,
      enableSorting: false,
      cell: ({ row }) => {
        const bill = purchaseBillById.get(row.original.purchaseBillId);
        return bill ? formatCurrency(bill.balanceAmount) : "—";
      },
      meta: { align: "right" },
    },
    createRowActionsColumn<SupplierPaymentAllocation>(rowActions),
  ];
}
