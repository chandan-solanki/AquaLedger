"use client";

import { Pencil, Trash2, Truck } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { SectionHeader } from "@/components/layout/section-header";
import { ExportMenu } from "@/components/reports";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import {
  SUPPLIER_STATUS_BADGE_VARIANT,
  SUPPLIER_STATUS_LABELS,
} from "@/features/suppliers/constants/supplier-status";
import { useDeleteSupplier } from "@/features/suppliers/hooks/use-delete-supplier";
import { useSupplier } from "@/features/suppliers/hooks/use-supplier";
import { triggerStatementDownload } from "@/features/reports/utils/trigger-report-download";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";

/**
 * Read-only Supplier record view - no Activity/Audit/Attachments, mirroring
 * `CompanyDetailPage`'s scope exactly. Delete opens the shared
 * `DeleteConfirmationDialog`; the actual mutation, its toast, and the
 * post-delete navigation all live in `useDeleteSupplier` so this page and
 * the List page's row action share identical behavior.
 */
export function SupplierDetailPage() {
  const params = useParams<{ id: string }>();
  const supplierId = params.id;
  const { hasPermission } = usePermissions();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const supplierQuery = useSupplier(supplierId);
  const deleteSupplier = useDeleteSupplier();

  if (!hasPermission("supplier:view")) {
    return (
      <ErrorState
        title="You don't have permission to view suppliers"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const supplier = supplierQuery.data;
  const apiError = supplierQuery.isError ? normalizeApiError(supplierQuery.error) : null;

  return (
    <DetailPageTemplate
      title={supplier?.name ?? "Supplier"}
      description={supplier?.code}
      icon={Truck}
      badge={
        supplier && (
          <Badge variant={SUPPLIER_STATUS_BADGE_VARIANT[supplier.status]}>
            {SUPPLIER_STATUS_LABELS[supplier.status]}
          </Badge>
        )
      }
      primaryAction={
        supplier && hasPermission("supplier:edit")
          ? { label: "Edit", icon: Pencil, href: `/suppliers/${supplier.id}/edit` }
          : undefined
      }
      secondaryActions={
        supplier && hasPermission("supplier:delete")
          ? [{ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) }]
          : undefined
      }
      exportMenu={
        supplier && hasPermission("reports:view") ? (
          <ExportMenu
            label="Download Statement"
            formats={["excel", "pdf"]}
            onExport={(format) => {
              if (format === "csv") return;
              triggerStatementDownload("supplier", format, { supplier_id: supplier.id });
            }}
          />
        ) : undefined
      }
      isLoading={supplierQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load supplier",
              description: apiError.message,
              onRetry: () => supplierQuery.refetch(),
            }
          : null
      }
    >
      {supplier && (
        <div className="space-y-6">
          <SectionHeader title="Supplier Information" />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <InfoCard title="Details">
              <DescriptionList
                items={[
                  { term: "Supplier Name", details: supplier.name },
                  { term: "Supplier Code", details: supplier.code },
                  { term: "GSTIN", details: supplier.gstin ?? "—" },
                  { term: "Phone", details: supplier.phone ?? "—" },
                  { term: "Email", details: supplier.email ?? "—" },
                  { term: "Status", details: SUPPLIER_STATUS_LABELS[supplier.status] },
                  { term: "Created At", details: formatDateTime(supplier.createdAt) },
                  { term: "Updated At", details: formatDateTime(supplier.updatedAt) },
                ]}
              />
            </InfoCard>

            <InfoCard title="Address">
              <DescriptionList
                items={[
                  { term: "Address", details: supplier.address ?? "—" },
                  { term: "City", details: supplier.city ?? "—" },
                  { term: "State", details: supplier.state ?? "—" },
                  { term: "Country", details: supplier.country ?? "—" },
                ]}
              />
            </InfoCard>
          </div>
        </div>
      )}

      {supplier && (
        <DeleteConfirmationDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
          entityName={supplier.name}
          entityLabel="supplier"
          isLoading={deleteSupplier.isPending}
          onConfirm={() => deleteSupplier.mutate(supplier.id)}
        />
      )}
    </DetailPageTemplate>
  );
}
