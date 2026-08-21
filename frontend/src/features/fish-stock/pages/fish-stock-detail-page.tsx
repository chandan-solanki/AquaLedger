"use client";

import { Fish as FishIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { ContentSection } from "@/components/layout/content-section";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/feedback/error-state";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { FishStockContributingCatchesTable } from "@/features/fish-stock/components/fish-stock-contributing-catches-table";
import { useFishStockDetail } from "@/features/fish-stock/hooks/use-fish-stock-detail";
import { FISH_STOCK_UNIT_LABELS } from "@/features/fish-stock/types/fish-stock";
import { useTripCatchInvoiceUsageSummary } from "@/features/invoices/hooks/use-trip-catch-invoice-usage-summary";
import type { TripCatchInvoiceUsage } from "@/features/invoices/types/trip-catch-invoice-usage";
import { normalizeApiError } from "@/utils/api-error";
import { formatQuantity } from "@/utils/format-number";

/**
 * Read-only Fish Stock detail (Sprint 15 Session 3): the fish's totals plus
 * every contributing trip catch, straight from the backend's
 * GET /fish-stock/{fish_id} (Session 2) - no field on this page is
 * recomputed or invented; everything shown comes directly off
 * `FishStockDetail`. Mirrors `FishDetailPage`'s read-only shape (no Edit/
 * Delete - this isn't the fish master record) and its "check the page's own
 * `fish:view` before rendering" gate.
 *
 * "Available" is the number this page exists to answer ("how much of this
 * fish can I still sell") - it gets its own prominent card, not just a row
 * in the summary list, per Session 3's explicit emphasis requirement.
 */
export function FishStockDetailPage() {
  const params = useParams<{ fishId: string }>();
  const fishId = params.fishId;
  const { hasPermission } = usePermissions();

  const detailQuery = useFishStockDetail(fishId);
  const tripCatchIds = useMemo(
    () => detailQuery.data?.catches.map((c) => c.tripCatchId) ?? [],
    [detailQuery.data]
  );
  const usageQuery = useTripCatchInvoiceUsageSummary(tripCatchIds);
  const usageByTripCatchId = useMemo(() => {
    // Sprint 15 Session 7: a failed usage-summary fetch degrades to "no
    // usage data available" (every catch shows a dash) rather than
    // breaking this page - Contributing Catches' own core data (caught/
    // sold/available/waste) is independent of this supplementary fetch.
    if (!usageQuery.data) return undefined;
    return new Map<string, TripCatchInvoiceUsage>(usageQuery.data.map((u) => [u.tripCatchId, u]));
  }, [usageQuery.data]);

  if (!hasPermission("fish:view")) {
    return (
      <ErrorState
        title="You don't have permission to view fish stock"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const detail = detailQuery.data;
  const apiError = detailQuery.isError ? normalizeApiError(detailQuery.error) : null;
  const isNotFound = apiError?.category === "not_found";

  return (
    <DetailPageTemplate
      title={detail?.fishName ?? "Fish Stock"}
      icon={FishIcon}
      badge={
        detail && Number(detail.totalAvailable) === 0 ? <Badge variant="secondary">Empty</Badge> : undefined
      }
      secondaryActions={
        detail ? [{ label: "View Fish Record", href: `/fish/${detail.fishId}` }] : undefined
      }
      isLoading={detailQuery.isLoading}
      error={
        apiError
          ? isNotFound
            ? { title: "Fish not found", description: "This fish doesn't exist or you don't have access to it." }
            : {
                title: "Failed to load fish stock",
                description: apiError.message,
                onRetry: () => detailQuery.refetch(),
              }
          : null
      }
    >
      {detail && (
        <div className="space-y-6">
          <InfoCard title="Available" className="border-primary/30">
            <p className="text-4xl font-bold text-primary tabular-nums">
              {formatQuantity(detail.totalAvailable)} {FISH_STOCK_UNIT_LABELS[detail.unit]}
            </p>
            <p className="text-sm text-muted-foreground">How much of this fish can still be sold.</p>
          </InfoCard>

          <InfoCard title="Stock Summary">
            <DescriptionList
              items={[
                { term: "Unit", details: FISH_STOCK_UNIT_LABELS[detail.unit] },
                { term: "Total Caught", details: `${formatQuantity(detail.totalCaught)} ${FISH_STOCK_UNIT_LABELS[detail.unit]}` },
                { term: "Total Sold", details: `${formatQuantity(detail.totalSold)} ${FISH_STOCK_UNIT_LABELS[detail.unit]}` },
                {
                  term: "Total Available",
                  details: `${formatQuantity(detail.totalAvailable)} ${FISH_STOCK_UNIT_LABELS[detail.unit]}`,
                },
                { term: "Total Waste", details: `${formatQuantity(detail.totalWaste)} ${FISH_STOCK_UNIT_LABELS[detail.unit]}` },
              ]}
            />
          </InfoCard>

          <ContentSection title="Contributing Catches">
            <FishStockContributingCatchesTable
              catches={detail.catches}
              isLoading={detailQuery.isLoading}
              usageByTripCatchId={usageByTripCatchId}
              isUsageLoading={usageQuery.isLoading}
              unitLabel={FISH_STOCK_UNIT_LABELS[detail.unit]}
            />
          </ContentSection>

          {hasPermission("invoice:create") && (
            <ContentSection>
              <Button variant="outline" asChild>
                <Link href="/invoices/new">Create Invoice</Link>
              </Button>
              <p className="mt-2 text-xs text-muted-foreground">
                Opens the invoice creation workflow without pre-selecting a catch - this fish has{" "}
                {detail.catches.length > 1 ? "multiple contributing catches" : "a specific contributing catch"},
                and stock is tracked per catch, not per fish. To start an invoice pre-loaded with one exact catch,
                use its own &ldquo;Create Invoice&rdquo; action in the Contributing Catches table below.
              </p>
            </ContentSection>
          )}
        </div>
      )}
    </DetailPageTemplate>
  );
}
