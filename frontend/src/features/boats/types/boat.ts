/**
 * Raw backend shape (snake_case), matching BoatResponse
 * (app/modules/boats/schemas.py) exactly. `capacity_kg` is a string - the
 * backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number.
 */
export interface BackendBoat {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  registration_number: string;
  license_number: string | null;
  boat_type: string | null;
  capacity_kg: string | null;
  engine_number: string | null;
  engine_hp: number | null;
  captain_name: string | null;
  captain_phone: string | null;
  insurance_expiry: string | null;
  license_expiry: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every boat-service.ts function returns. */
export interface Boat {
  id: string;
  tenantId: string;
  code: string;
  name: string;
  registrationNumber: string;
  licenseNumber: string | null;
  boatType: string | null;
  capacityKg: string | null;
  engineNumber: string | null;
  engineHp: number | null;
  captainName: string | null;
  captainPhone: string | null;
  insuranceExpiry: string | null;
  licenseExpiry: string | null;
  notes: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendBoat(boat: BackendBoat): Boat {
  return {
    id: boat.id,
    tenantId: boat.tenant_id,
    code: boat.code,
    name: boat.name,
    registrationNumber: boat.registration_number,
    licenseNumber: boat.license_number,
    boatType: boat.boat_type,
    capacityKg: boat.capacity_kg,
    engineNumber: boat.engine_number,
    engineHp: boat.engine_hp,
    captainName: boat.captain_name,
    captainPhone: boat.captain_phone,
    insuranceExpiry: boat.insurance_expiry,
    licenseExpiry: boat.license_expiry,
    notes: boat.notes,
    isActive: boat.is_active,
    createdAt: boat.created_at,
    updatedAt: boat.updated_at,
  };
}

/**
 * Query params for GET /boats (app/modules/boats/schemas.py's
 * BoatListParams) - snake_case to match the wire format exactly, since
 * `boat-service.ts` forwards these straight through as a query string.
 */
export interface BoatListParams {
  q?: string;
  boat_type?: string;
  is_active?: boolean;
  insurance_expired?: boolean;
  license_expired?: boolean;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /boats (BoatCreateRequest, app/modules/boats/schemas.py)
 * - snake_case to match the wire format exactly. `code`, `name` and
 * `registration_number` are required; every other field the backend
 * defaults or accepts as null when omitted. Boat ownership is the tenant
 * only - there is no `company_id` (a `Company` is a customer, never a boat
 * owner).
 */
export interface BoatCreateRequest {
  code: string;
  name: string;
  registration_number: string;
  license_number?: string;
  boat_type?: string;
  capacity_kg?: string;
  engine_number?: string;
  engine_hp?: number;
  captain_name?: string;
  captain_phone?: string;
  insurance_expiry?: string;
  license_expiry?: string;
  notes?: string;
  is_active?: boolean;
}

/** Request body for PUT /boats/{id} (BoatUpdateRequest) - a partial update, only present fields change. */
export type BoatUpdateRequest = Partial<BoatCreateRequest>;
