import { Fish, Package, PackageCheck } from "lucide-react";

import { MetricCard } from "@/components/data-display/metric-card";
import { SummaryGrid } from "@/components/data-display/summary-grid";
import { FISH_STOCK_UNIT_LABELS } from "@/features/fish-stock/types/fish-stock";
import type { FishStockRow } from "@/features/fish-stock/types/fish-stock";
import { formatQuantity } from "@/utils/format-number";

interface FishStockSummaryCardsProps {
  /** The current page's rows - only summed into a KPI when they cover every matching fish (see `sumAcrossFullResultOnly`). */
  rows: FishStockRow[];
  /** `meta.total_records` - the true count of matching fish across every page, always safe to show as-is. */
  totalFishTypes: number;
}

const MIXED_UNITS_NOTE = "Mixed units — see table";
const MORE_THAN_ONE_PAGE_NOTE = "More fish than shown — see table";

/**
 * A quantity total is only meaningful if every matching fish is actually
 * being summed (not just the current page) AND they all share one unit -
 * Fish.unit can be KG, BOX, PIECE or TON (Sprint 15 Session 1 §6/§13), and
 * silently adding kilograms to boxes would be a meaningless number. When
 * either condition fails, this returns `null` so the caller falls back to
 * the safe "view by fish" copy instead of a misleading combined figure.
 */
function sumAcrossFullResultOnly(
  rows: FishStockRow[],
  totalFishTypes: number,
  key: "totalCaught" | "totalSold" | "totalAvailable"
): { value: string; note?: string } | null {
  if (rows.length === 0) return null;
  if (rows.length < totalFishTypes) return { value: "View by fish", note: MORE_THAN_ONE_PAGE_NOTE };

  const unit = rows[0].unit;
  const singleUnit = rows.every((row) => row.unit === unit);
  if (!singleUnit) return { value: "View by fish", note: MIXED_UNITS_NOTE };

  const total = rows.reduce((sum, row) => sum + Number(row[key]), 0);
  return { value: `${formatQuantity(total)} ${FISH_STOCK_UNIT_LABELS[unit]}` };
}

/**
 * Fish Stock's KPI row (Sprint 15 Session 3): Total Available, Total Caught,
 * Total Sold, Fish Types. `totalFishTypes` (the backend's `meta.total_records`)
 * is always shown as a plain count - it's never a quantity, so unit-mixing
 * doesn't apply. The three quantity cards degrade to "View by fish" rather
 * than ever combining different units or summing only a partial page into a
 * total, per Session 3's explicit instruction not to produce a misleading
 * global number.
 */
export function FishStockSummaryCards({ rows, totalFishTypes }: FishStockSummaryCardsProps) {
  const available = sumAcrossFullResultOnly(rows, totalFishTypes, "totalAvailable");
  const caught = sumAcrossFullResultOnly(rows, totalFishTypes, "totalCaught");
  const sold = sumAcrossFullResultOnly(rows, totalFishTypes, "totalSold");

  return (
    <SummaryGrid columns={4}>
      <MetricCard
        title="Total Available"
        value={available?.value ?? "View by fish"}
        description={available?.note}
        icon={PackageCheck}
      />
      <MetricCard
        title="Total Caught"
        value={caught?.value ?? "View by fish"}
        description={caught?.note}
        icon={Package}
      />
      <MetricCard
        title="Total Sold"
        value={sold?.value ?? "View by fish"}
        description={sold?.note}
        icon={Package}
      />
      <MetricCard title="Fish Types" value={String(totalFishTypes)} icon={Fish} />
    </SummaryGrid>
  );
}
