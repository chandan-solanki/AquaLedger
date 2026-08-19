"use client";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { ErrorState } from "@/components/feedback/error-state";
import { SettingsPageTemplate } from "@/components/templates/settings-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getNumberingSequenceColumns } from "@/features/numbering-sequences/components/numbering-sequence-columns";
import { useNumberingSequences } from "@/features/numbering-sequences/hooks/use-numbering-sequences";
import { normalizeApiError } from "@/utils/api-error";

const SETTINGS_MANAGE_PERMISSION = "settings:manage";

/**
 * Settings > Numbering Sequences (Sprint 14 Session 2): a read-only view
 * over the six independent, already-safe sequence allocators (invoices,
 * purchase bills, purchase orders, customer payments, supplier payments,
 * delivery challans). No Edit action - the audit backing this page found
 * prefix/fiscal year are hardcoded per module today, so there is nothing
 * safe to configure yet without inventing new, unrequested per-tenant
 * configuration. Mirrors CompanyProfilePage's permission-gate shape
 * exactly.
 */
export function NumberingSequencesPage() {
  const { hasPermission } = usePermissions();
  const sequencesQuery = useNumberingSequences();
  const sequences = sequencesQuery.data ?? [];
  const apiError = sequencesQuery.isError ? normalizeApiError(sequencesQuery.error) : null;
  const columns = getNumberingSequenceColumns();
  const table = useDataTable({ data: sequences, columns });

  if (!hasPermission(SETTINGS_MANAGE_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to view numbering sequences"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  return (
    <SettingsPageTemplate
      title="Numbering Sequences"
      description="Configure how AquaLedger generates business document numbers."
    >
      <DataTable
        table={table}
        isLoading={sequencesQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load numbering sequences",
                description: apiError.message,
                onRetry: () => sequencesQuery.refetch(),
              }
            : null
        }
        isEmpty={!sequencesQuery.isLoading && !apiError && sequences.length === 0}
        emptyState={
          <DataTableEmpty
            title="No numbering sequences found"
            description="Document numbering will appear here once configured."
          />
        }
        aria-label="Numbering sequences"
      />
    </SettingsPageTemplate>
  );
}
