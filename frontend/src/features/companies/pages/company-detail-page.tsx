"use client";

import { Building2, Pencil, Trash2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SectionHeader } from "@/components/layout/section-header";
import { ExportMenu } from "@/components/reports";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import {
  COMPANY_STATUS_BADGE_VARIANT,
  COMPANY_STATUS_LABELS,
} from "@/features/companies/constants/company-status";
import { COMPANY_TYPE_LABELS } from "@/features/companies/constants/company-type";
import { useCompany } from "@/features/companies/hooks/use-company";
import { useDeleteCompany } from "@/features/companies/hooks/use-delete-company";
import { triggerStatementDownload } from "@/features/reports/utils/trigger-report-download";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";

/**
 * Read-only Company record view - no editing, no Activity/Audit/Attachments
 * (Sprint 3 Session 3's explicit scope). Delete opens the shared
 * `DeleteConfirmationDialog`; the actual mutation, its toast, and the
 * post-delete navigation all live in `useDeleteCompany` so this page and the
 * List page's row action share identical behavior.
 */
export function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const companyId = params.id;
  const { hasPermission } = usePermissions();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const companyQuery = useCompany(companyId);
  const deleteCompany = useDeleteCompany();

  if (!hasPermission("company:view")) {
    return (
      <ErrorState
        title="You don't have permission to view companies"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const company = companyQuery.data;
  const apiError = companyQuery.isError ? normalizeApiError(companyQuery.error) : null;

  return (
    <DetailPageTemplate
      title={company?.name ?? "Company"}
      description={company?.code}
      icon={Building2}
      badge={
        company && (
          <Badge variant={COMPANY_STATUS_BADGE_VARIANT[company.status]}>
            {COMPANY_STATUS_LABELS[company.status]}
          </Badge>
        )
      }
      primaryAction={
        company && hasPermission("company:edit")
          ? { label: "Edit", icon: Pencil, href: `/companies/${company.id}/edit` }
          : undefined
      }
      secondaryActions={
        company && hasPermission("company:delete")
          ? [{ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) }]
          : undefined
      }
      exportMenu={
        company && hasPermission("reports:view") ? (
          <ExportMenu
            label="Download Statement"
            formats={["excel", "pdf"]}
            onExport={(format) => {
              if (format === "csv") return;
              triggerStatementDownload("customer", format, { customer_id: company.id });
            }}
          />
        ) : undefined
      }
      isLoading={companyQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load company",
              description: apiError.message,
              onRetry: () => companyQuery.refetch(),
            }
          : null
      }
    >
      {company && (
        <div className="space-y-6">
          <SectionHeader title="Company Information" />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <InfoCard title="Details">
              <DescriptionList
                items={[
                  { term: "Company Name", details: company.name },
                  { term: "Company Code", details: company.code },
                  { term: "Company Type", details: COMPANY_TYPE_LABELS[company.companyType] },
                  { term: "GSTIN", details: company.gstin ?? "—" },
                  { term: "Phone", details: company.phone ?? "—" },
                  { term: "Email", details: company.email ?? "—" },
                  { term: "Status", details: COMPANY_STATUS_LABELS[company.status] },
                  { term: "Created At", details: formatDateTime(company.createdAt) },
                  { term: "Updated At", details: formatDateTime(company.updatedAt) },
                ]}
              />
            </InfoCard>

            <InfoCard title="Address">
              <DescriptionList
                items={[
                  { term: "Address", details: company.addressLine1 ?? "—" },
                  { term: "City", details: company.city ?? "—" },
                  { term: "State", details: company.state ?? "—" },
                  { term: "Country", details: company.country ?? "—" },
                  { term: "Postal Code", details: company.pincode ?? "—" },
                ]}
              />
            </InfoCard>
          </div>

          <InfoCard title="Notes">
            {company.notes ? (
              <p className="text-sm whitespace-pre-wrap">{company.notes}</p>
            ) : (
              <EmptyState title="No notes added" description="Notes for this company will appear here." />
            )}
          </InfoCard>
        </div>
      )}

      {company && (
        <DeleteConfirmationDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
          entityName={company.name}
          entityLabel="company"
          isLoading={deleteCompany.isPending}
          onConfirm={() => deleteCompany.mutate(company.id)}
        />
      )}
    </DetailPageTemplate>
  );
}
