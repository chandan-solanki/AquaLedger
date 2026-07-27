/** Mirrors the backend's CatchGrade enum (app/modules/trip_catches/constants.py). */
export type CatchGrade = "A" | "B" | "C";

/**
 * Raw backend shape (snake_case), matching TripCatchResponse
 * (app/modules/trip_catches/schemas.py) exactly. Quantity fields are
 * strings - the backend serializes `Decimal` as a JSON string, never a
 * float (ARCHITECTURE.md §5.1), and the client keeps that representation
 * rather than parsing into a JS number. There is no nested trip or fish
 * object - only `trip_id`/`fish_id` - so a fish's display name/unit is
 * resolved client-side via the Fish feature's own public service (see
 * `use-fish-options.ts`), the same way `boat_id` is resolved on Trip.
 */
export interface BackendTripCatch {
  id: string;
  tenant_id: string;
  trip_id: string;
  fish_id: string;
  grade: CatchGrade | null;
  quantity_caught: string;
  available_quantity: string;
  sold_quantity: string;
  waste_quantity: string;
  landing_date: string;
  landing_port: string | null;
  remarks: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every trip-catch-service.ts function returns. */
export interface TripCatch {
  id: string;
  tenantId: string;
  tripId: string;
  fishId: string;
  grade: CatchGrade | null;
  quantityCaught: string;
  availableQuantity: string;
  soldQuantity: string;
  wasteQuantity: string;
  landingDate: string;
  landingPort: string | null;
  remarks: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendTripCatch(tripCatch: BackendTripCatch): TripCatch {
  return {
    id: tripCatch.id,
    tenantId: tripCatch.tenant_id,
    tripId: tripCatch.trip_id,
    fishId: tripCatch.fish_id,
    grade: tripCatch.grade,
    quantityCaught: tripCatch.quantity_caught,
    availableQuantity: tripCatch.available_quantity,
    soldQuantity: tripCatch.sold_quantity,
    wasteQuantity: tripCatch.waste_quantity,
    landingDate: tripCatch.landing_date,
    landingPort: tripCatch.landing_port,
    remarks: tripCatch.remarks,
    createdAt: tripCatch.created_at,
    updatedAt: tripCatch.updated_at,
  };
}

/**
 * Query params for GET /trip-catches (app/modules/trip_catches/schemas.py's
 * TripCatchListParams) - snake_case to match the wire format exactly.
 * `use-trip-catches.ts` only ever populates `trip_id`/`page`/`page_size`
 * this session - the `q`/`fish_id`/`grade`/date-range filters the backend
 * already supports are left unwired since Trip Catch has no filter UI here
 * (a bounded, read-only sub-table scoped to one trip, not a list page).
 */
export interface TripCatchListParams {
  q?: string;
  trip_id?: string;
  fish_id?: string;
  grade?: CatchGrade;
  landing_date_from?: string;
  landing_date_to?: string;
  sort?: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /trip-catches (TripCatchCreateRequest,
 * app/modules/trip_catches/schemas.py) - snake_case to match the wire
 * format exactly. `trip_id`, `fish_id`, `quantity_caught` and
 * `landing_date` are required. `available_quantity`/`sold_quantity`/
 * `waste_quantity` are deliberately absent - the backend fixes them to
 * `quantity_caught`/`0`/`0` server-side at creation and silently ignores
 * those keys if a client sends them, so there is nothing to type here.
 */
export interface TripCatchCreateRequest {
  trip_id: string;
  fish_id: string;
  grade?: CatchGrade;
  quantity_caught: string;
  landing_date: string;
  landing_port?: string;
  remarks?: string;
}

/**
 * Request body for PUT /trip-catches/{id} (TripCatchUpdateRequest) - a
 * partial update, only present fields change. Unlike create,
 * `available_quantity`/`sold_quantity`/`waste_quantity` ARE editable here -
 * the backend re-validates `available + sold + waste == quantity_caught`
 * against the merged result (422 `TRIP_CATCH_QUANTITY_INVARIANT_VIOLATION`
 * otherwise).
 */
export interface TripCatchUpdateRequest {
  trip_id?: string;
  fish_id?: string;
  grade?: CatchGrade;
  quantity_caught?: string;
  available_quantity?: string;
  sold_quantity?: string;
  waste_quantity?: string;
  landing_date?: string;
  landing_port?: string;
  remarks?: string;
}
