"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Route, TrendingDown, TrendingUp, Wallet } from "lucide-react";

import { MetricCard } from "@/components/data-display/metric-card";
import { SummaryGrid } from "@/components/data-display/summary-grid";
import { InfoCard } from "@/components/data-display/info-card";
import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { CardSkeleton } from "@/components/feedback/skeletons/card-skeleton";
import { SectionHeader } from "@/components/layout/section-header";
import { getBoatTripHistoryColumns } from "@/features/boats/components/boat-trip-history-columns";
import {
  DEFAULT_TRIP_PROFITABILITY_FILTERS,
  useBoatLifetimeProfitability,
  useTripProfitability,
} from "@/features/reports";
import type { TripProfitabilityRow } from "@/features/reports";
import { formatCurrency } from "@/utils/format-currency";
import { normalizeApiError } from "@/utils/api-error";

export interface BoatProfitabilityTabProps {
  boatId: string;
}

/**
 * The Boat Detail page's Profitability tab (TASKS.md Sprint 11 Session 4
 * Phase A "ADD NEW TAB") - a Lifetime Summary (this one boat's own row
 * from GET /reports/boat-profitability, narrowed to `boat_id` with no date
 * range) plus its full Trip History (every completed trip belonging to it,
 * from GET /reports/trip-profitability, same `boat_id` narrowing). Both
 * reuse the Reports feature's own public hooks/types - never duplicated
 * calculations, per TASKS.md's "Do NOT duplicate calculations."
 */
export function BoatProfitabilityTab({ boatId }: BoatProfitabilityTabProps) {
  const lifetimeQuery = useBoatLifetimeProfitability(boatId);
  const tripHistoryFilters = useMemo(
    () => ({ ...DEFAULT_TRIP_PROFITABILITY_FILTERS, boatId, pageSize: 100 }),
    [boatId]
  );
  const tripHistoryQuery = useTripProfitability(tripHistoryFilters);

  const boatRow = lifetimeQuery.data?.rows[0];
  const lifetimeError = lifetimeQuery.isError ? normalizeApiError(lifetimeQuery.error) : null;

  const trips = useMemo(() => tripHistoryQuery.data?.rows ?? [], [tripHistoryQuery.data]);
  const tripHistoryError = tripHistoryQuery.isError
    ? normalizeApiError(tripHistoryQuery.error)
    : null;
  const tripHistoryColumns = useMemo(() => getBoatTripHistoryColumns(), []);
  const table = useDataTable({ data: trips, columns: tripHistoryColumns });

  const router = useRouter();

  return (
    <div className="space-y-6">
      <SectionHeader title="Lifetime Summary" />
      {lifetimeQuery.isLoading ? (
        <CardSkeleton lines={4} />
      ) : lifetimeError ? (
        <ErrorState
          title="Failed to load profitability summary"
          description={lifetimeError.message}
          onRetry={() => lifetimeQuery.refetch()}
        />
      ) : boatRow ? (
        <SummaryGrid columns={4}>
          <MetricCard title="Revenue" value={formatCurrency(boatRow.revenue)} icon={TrendingUp} />
          <MetricCard title="Expenses" value={formatCurrency(boatRow.expenses)} icon={TrendingDown} />
          <MetricCard title="Profit" value={formatCurrency(boatRow.profit)} icon={Wallet} />
          <MetricCard title="Profit Margin" value={`${boatRow.profitMarginPercent}%`} icon={TrendingUp} />
          <MetricCard
            title="Average Profit Per Trip"
            value={formatCurrency(boatRow.averageProfitPerTrip)}
            icon={TrendingUp}
          />
          <MetricCard title="Total Trips" value={String(boatRow.totalTrips)} icon={Route} />
          <MetricCard title="Best Trip" value={formatCurrency(boatRow.bestTripProfit)} icon={TrendingUp} />
          <MetricCard title="Worst Trip" value={formatCurrency(boatRow.worstTripProfit)} icon={TrendingDown} />
        </SummaryGrid>
      ) : (
        <EmptyState
          title="No completed trips yet"
          description="This boat's profitability summary will appear here once it has at least one completed trip."
        />
      )}

      <SectionHeader title="Trip History" />
      <InfoCard>
        <DataTable
          table={table}
          isLoading={tripHistoryQuery.isLoading}
          error={
            tripHistoryError
              ? {
                  title: "Failed to load trip history",
                  description: tripHistoryError.message,
                  onRetry: () => tripHistoryQuery.refetch(),
                }
              : null
          }
          isEmpty={!tripHistoryQuery.isLoading && !tripHistoryError && trips.length === 0}
          emptyState={
            <DataTableEmpty
              title="No completed trips yet"
              description="Completed trips for this boat will appear here."
            />
          }
          onRowClick={(row: TripProfitabilityRow) => router.push(`/trips/${row.tripId}`)}
          stickyActionColumn
          aria-label="Trip history"
        />
      </InfoCard>
    </div>
  );
}
