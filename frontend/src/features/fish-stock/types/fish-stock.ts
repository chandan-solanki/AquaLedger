/**
 * Mirrors the backend's FishUnit enum (app/modules/fish/constants.py) as
 * surfaced on FishStockRow/FishStockDetail (app/modules/trip_catches/
 * schemas.py). A local copy, not imported from the `fish` feature - each
 * feature keeps its own copy of small shared vocabulary rather than
 * reaching into another feature's internals (mirrors `fish-sales-columns.tsx`'s
 * own stated rule for the same enum).
 */
export type FishStockUnit = "kg" | "box" | "piece" | "ton";

export const FISH_STOCK_UNIT_LABELS: Record<FishStockUnit, string> = {
  kg: "Kg",
  box: "Box",
  piece: "Piece",
  ton: "Ton",
};

/**
 * Raw backend shape (snake_case), matching FishStockRow
 * (app/modules/trip_catches/schemas.py) exactly. Every quantity is a
 * string - the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1). There is no `fish_code` field on this response -
 * the backend schema doesn't return one, so none is invented here.
 */
export interface BackendFishStockRow {
  fish_id: string;
  fish_name: string;
  unit: FishStockUnit;
  total_caught: string;
  total_sold: string;
  total_available: string;
  total_waste: string;
}

/** The client-facing, camelCase shape fishStockService.listFishStock returns. */
export interface FishStockRow {
  fishId: string;
  fishName: string;
  unit: FishStockUnit;
  totalCaught: string;
  totalSold: string;
  totalAvailable: string;
  totalWaste: string;
}

export function mapBackendFishStockRow(row: BackendFishStockRow): FishStockRow {
  return {
    fishId: row.fish_id,
    fishName: row.fish_name,
    unit: row.unit,
    totalCaught: row.total_caught,
    totalSold: row.total_sold,
    totalAvailable: row.total_available,
    totalWaste: row.total_waste,
  };
}

/**
 * Query params for GET /fish-stock (app/modules/trip_catches/schemas.py's
 * FishStockListParams) - snake_case to match the wire format exactly. No
 * `sort` param - the backend always orders by fish name ascending, a fixed
 * order, the same posture `FishSalesParams` takes for its own fixed order.
 */
export interface FishStockListParams {
  q?: string;
  is_active?: boolean;
  page: number;
  page_size: number;
}

/**
 * Raw backend shape for one contributing trip catch on the detail response
 * (FishStockContributingCatch, app/modules/trip_catches/schemas.py) -
 * exactly the fields the backend returns, nothing more.
 */
export interface BackendFishStockContributingCatch {
  trip_catch_id: string;
  trip_id: string;
  trip_number: string;
  landing_date: string;
  quantity_caught: string;
  sold_quantity: string;
  available_quantity: string;
  waste_quantity: string;
}

export interface FishStockContributingCatch {
  tripCatchId: string;
  tripId: string;
  tripNumber: string;
  landingDate: string;
  quantityCaught: string;
  soldQuantity: string;
  availableQuantity: string;
  wasteQuantity: string;
}

/** Raw backend shape for GET /fish-stock/{fish_id} (FishStockDetail). */
export interface BackendFishStockDetail {
  fish_id: string;
  fish_name: string;
  unit: FishStockUnit;
  total_caught: string;
  total_sold: string;
  total_available: string;
  total_waste: string;
  catches: BackendFishStockContributingCatch[];
}

export interface FishStockDetail {
  fishId: string;
  fishName: string;
  unit: FishStockUnit;
  totalCaught: string;
  totalSold: string;
  totalAvailable: string;
  totalWaste: string;
  catches: FishStockContributingCatch[];
}

export function mapBackendFishStockDetail(detail: BackendFishStockDetail): FishStockDetail {
  return {
    fishId: detail.fish_id,
    fishName: detail.fish_name,
    unit: detail.unit,
    totalCaught: detail.total_caught,
    totalSold: detail.total_sold,
    totalAvailable: detail.total_available,
    totalWaste: detail.total_waste,
    catches: detail.catches.map((catchRow) => ({
      tripCatchId: catchRow.trip_catch_id,
      tripId: catchRow.trip_id,
      tripNumber: catchRow.trip_number,
      landingDate: catchRow.landing_date,
      quantityCaught: catchRow.quantity_caught,
      soldQuantity: catchRow.sold_quantity,
      availableQuantity: catchRow.available_quantity,
      wasteQuantity: catchRow.waste_quantity,
    })),
  };
}
