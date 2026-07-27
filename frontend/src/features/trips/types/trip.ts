/** Mirrors the backend's TripStatus enum (app/modules/trips/constants.py). */
export type TripStatus = "planned" | "departed" | "returned" | "cancelled";

/** Mirrors the backend's TripType enum (app/modules/trips/constants.py). */
export type TripType = "fishing" | "transport" | "maintenance" | "other";

/**
 * Raw backend shape (snake_case), matching TripResponse
 * (app/modules/trips/schemas.py) exactly. There is no nested boat object -
 * only `boat_id` - so a boat's display name is resolved client-side via the
 * Boats feature's own public service (see `use-boat-options.ts`).
 */
export interface BackendTrip {
  id: string;
  tenant_id: string;
  boat_id: string;
  trip_number: string;
  trip_type: TripType;
  captain_name: string | null;
  departure_port: string | null;
  arrival_port: string | null;
  departure_datetime: string;
  expected_return_datetime: string | null;
  actual_return_datetime: string | null;
  status: TripStatus;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every trip-service.ts function returns. */
export interface Trip {
  id: string;
  tenantId: string;
  boatId: string;
  tripNumber: string;
  tripType: TripType;
  captainName: string | null;
  departurePort: string | null;
  arrivalPort: string | null;
  departureDatetime: string;
  expectedReturnDatetime: string | null;
  actualReturnDatetime: string | null;
  status: TripStatus;
  notes: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendTrip(trip: BackendTrip): Trip {
  return {
    id: trip.id,
    tenantId: trip.tenant_id,
    boatId: trip.boat_id,
    tripNumber: trip.trip_number,
    tripType: trip.trip_type,
    captainName: trip.captain_name,
    departurePort: trip.departure_port,
    arrivalPort: trip.arrival_port,
    departureDatetime: trip.departure_datetime,
    expectedReturnDatetime: trip.expected_return_datetime,
    actualReturnDatetime: trip.actual_return_datetime,
    status: trip.status,
    notes: trip.notes,
    isActive: trip.is_active,
    createdAt: trip.created_at,
    updatedAt: trip.updated_at,
  };
}

/**
 * Query params for GET /trips (app/modules/trips/schemas.py's
 * TripListParams) - snake_case to match the wire format exactly, since
 * `trip-service.ts` forwards these straight through as a query string.
 * Only `q`/`boat_id`/`status`/`sort`/`page`/`page_size` are wired to UI
 * controls this session (see `toTripListParams`); the date-range and
 * `trip_type` filters the backend already supports are left for a later
 * session's filter panel.
 */
export interface TripListParams {
  q?: string;
  boat_id?: string;
  status?: TripStatus;
  trip_type?: TripType;
  departure_date_from?: string;
  departure_date_to?: string;
  return_date_from?: string;
  return_date_to?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /trips (TripCreateRequest, app/modules/trips/schemas.py)
 * - snake_case to match the wire format exactly. `boat_id`, `trip_number`
 * and `trip_type` are required; every other field the backend defaults or
 * accepts as null when omitted. `tenant_id`/`created_by`/`updated_by` are
 * never client-supplied - the router populates them from the authenticated
 * user.
 */
export interface TripCreateRequest {
  boat_id: string;
  trip_number: string;
  trip_type: TripType;
  captain_name?: string;
  departure_port?: string;
  arrival_port?: string;
  departure_datetime: string;
  expected_return_datetime?: string;
  actual_return_datetime?: string;
  status?: TripStatus;
  notes?: string;
  is_active?: boolean;
}

/** Request body for PUT /trips/{id} (TripUpdateRequest) - a partial update, only present fields change. */
export type TripUpdateRequest = Partial<TripCreateRequest>;
