"use client";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { ContentSection } from "@/components/layout/content-section";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getPurchaseOrderLinkedBillColumns } from "@/features/purchase-orders/components/purchase-order-linked-bill-columns";
import { usePurchaseOrderLinkedBills } from "@/features/purchase-orders/hooks/use-purchase-order-linked-bills";
import { normalizeApiError } from "@/utils/api-error";

export interface PurchaseOrderLinkedBillsTableProps {
  purchaseOrderId: string;
}

/**
 * The Purchase Order Detail page's "Purchase Bills" section (Sprint 12
 * Session 13) - every Purchase Bill linked to this order, in one aggregated
 * request (`usePurchaseOrderLinkedBills`), never one request per bill.
 * Read-only: no add/edit/delete, mirroring `PurchaseOrderItemTable`'s
 * DataTable usage minus the CRUD dialogs, since this table offers nothing
 * but navigation to each bill.
 */
export function PurchaseOrderLinkedBillsTable({ purchaseOrderId }: PurchaseOrderLinkedBillsTableProps) {
  const { hasPermission } = usePermissions();
  const billsQuery = usePurchaseOrderLinkedBills(purchaseOrderId);
  const bills = billsQuery.data ?? [];
  const apiError = billsQuery.isError ? normalizeApiError(billsQuery.error) : null;
  const columns = getPurchaseOrderLinkedBillColumns(hasPermission("purchase:view"));
  const table = useDataTable({ data: bills, columns });

  return (
    <ContentSection title="Purchase Bills">
      <DataTable
        table={table}
        isLoading={billsQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load linked purchase bills",
                description: apiError.message,
                onRetry: () => billsQuery.refetch(),
              }
            : null
        }
        isEmpty={!billsQuery.isLoading && !apiError && bills.length === 0}
        emptyState={
          <DataTableEmpty
            title="No purchase bills yet"
            description="Purchase bills created against this purchase order will appear here."
          />
        }
        aria-label="Linked purchase bills"
      />
    </ContentSection>
  );
}
