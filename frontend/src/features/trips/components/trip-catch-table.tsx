"use client";

import { useMemo, useState } from "react";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { InfoCard } from "@/components/data-display/info-card";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { getTripCatchColumns } from "@/features/trips/components/trip-catch-columns";
import { useTripCatchRowActions } from "@/features/trips/components/trip-catch-row-actions";
import { useDeleteTripCatch } from "@/features/trips/hooks/use-delete-trip-catch";
import { useFishOptions } from "@/features/trips/hooks/use-fish-options";
import { useTripCatches } from "@/features/trips/hooks/use-trip-catches";
import type { TripCatch } from "@/features/trips/types/trip-catch";
import { normalizeApiError } from "@/utils/api-error";

export interface TripCatchTableProps {
  tripId: string;
}

/**
 * The Trip Detail page's Catch section - a bounded sub-table of every
 * `trip_catches` row for this one trip (fetched via `trip_id`, since
 * `trip-catches` is its own top-level backend resource, not nested under
 * `/trips/{id}` or embedded in `TripResponse` - see `trip-catch-service.ts`).
 * No search/filter/sort/pagination UI: the whole set is fetched in one page
 * (`useTripCatches`'s own max page_size) and rendered as-is, since a single
 * trip's catch count is small and bounded.
 *
 * Owns its own row-level Delete flow (`useDeleteTripCatch` + the shared
 * `DeleteConfirmationDialog`) - View/Edit are row-action navigation
 * (`useTripCatchRowActions`) to `/trips/{tripId}/catches/{catchId}/edit`.
 * Create ("Add Catch") is a page-level action rendered by the Trip Detail
 * page itself, not this table.
 */
export function TripCatchTable({ tripId }: TripCatchTableProps) {
  const [pendingDelete, setPendingDelete] = useState<TripCatch | null>(null);

  const catchesQuery = useTripCatches(tripId);
  const fishOptions = useFishOptions();
  const deleteTripCatch = useDeleteTripCatch();
  const catches = useMemo(() => catchesQuery.data?.data ?? [], [catchesQuery.data]);
  const apiError = catchesQuery.isError ? normalizeApiError(catchesQuery.error) : null;

  const rowActionsFor = useTripCatchRowActions(tripId, setPendingDelete);
  const columns = useMemo(
    () => getTripCatchColumns(fishOptions.fishById, rowActionsFor),
    [fishOptions.fishById, rowActionsFor]
  );
  const table = useDataTable({ data: catches, columns });

  return (
    <InfoCard>
      <DataTable
        table={table}
        isLoading={catchesQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load trip catch records",
                description: apiError.message,
                onRetry: () => catchesQuery.refetch(),
              }
            : null
        }
        isEmpty={!catchesQuery.isLoading && !apiError && catches.length === 0}
        emptyState={
          <DataTableEmpty title="No catch recorded" description="Catch records for this trip will appear here." />
        }
        stickyActionColumn
        aria-label="Trip catch"
      />

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={fishOptions.fishById.get(pendingDelete.fishId)?.name ?? "this catch record"}
          entityLabel="trip catch"
          isLoading={deleteTripCatch.isPending}
          onConfirm={() =>
            deleteTripCatch.mutate({ id: pendingDelete.id, tripId }, { onSuccess: () => setPendingDelete(null) })
          }
        />
      )}
    </InfoCard>
  );
}
