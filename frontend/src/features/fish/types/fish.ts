/** Mirrors the backend's FishUnit enum (app/modules/fish/constants.py). */
export type FishUnit = "kg" | "box" | "piece" | "ton";

export const FISH_UNIT_VALUES = ["kg", "box", "piece", "ton"] as const satisfies readonly FishUnit[];

export const FISH_UNIT_LABELS: Record<FishUnit, string> = {
  kg: "Kg",
  box: "Box",
  piece: "Piece",
  ton: "Ton",
};

/** `{ value, label }` pairs derived from `FISH_UNIT_LABELS` - shared by the list page's Unit filter and `FishForm`'s Unit select so neither redefines the option set. */
export const FISH_UNIT_OPTIONS = FISH_UNIT_VALUES.map((value) => ({
  value,
  label: FISH_UNIT_LABELS[value],
}));

/**
 * Raw backend shape (snake_case), matching FishResponse
 * (app/modules/fish/schemas.py) exactly. Rate fields are strings - the
 * backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number.
 */
export interface BackendFish {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  local_name: string | null;
  scientific_name: string | null;
  category: string | null;
  unit: FishUnit;
  default_purchase_rate: string | null;
  default_sale_rate: string | null;
  hsn_code: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every fish-service.ts function returns. */
export interface Fish {
  id: string;
  tenantId: string;
  code: string;
  name: string;
  localName: string | null;
  scientificName: string | null;
  category: string | null;
  unit: FishUnit;
  defaultPurchaseRate: string | null;
  defaultSaleRate: string | null;
  hsnCode: string | null;
  description: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendFish(fish: BackendFish): Fish {
  return {
    id: fish.id,
    tenantId: fish.tenant_id,
    code: fish.code,
    name: fish.name,
    localName: fish.local_name,
    scientificName: fish.scientific_name,
    category: fish.category,
    unit: fish.unit,
    defaultPurchaseRate: fish.default_purchase_rate,
    defaultSaleRate: fish.default_sale_rate,
    hsnCode: fish.hsn_code,
    description: fish.description,
    isActive: fish.is_active,
    createdAt: fish.created_at,
    updatedAt: fish.updated_at,
  };
}

/**
 * Query params for GET /fish (app/modules/fish/schemas.py's FishListParams)
 * - snake_case to match the wire format exactly, since `fish-service.ts`
 * forwards these straight through as a query string.
 */
export interface FishListParams {
  q?: string;
  category?: string;
  unit?: FishUnit;
  is_active?: boolean;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /fish (FishCreateRequest, app/modules/fish/schemas.py)
 * - snake_case to match the wire format exactly. Only `code` and `name` are
 * required; every other field the backend defaults or accepts as null when
 * omitted.
 */
export interface FishCreateRequest {
  code: string;
  name: string;
  local_name?: string;
  scientific_name?: string;
  category?: string;
  unit?: FishUnit;
  default_purchase_rate?: string;
  default_sale_rate?: string;
  hsn_code?: string;
  description?: string;
  is_active?: boolean;
}

/** Request body for PUT /fish/{id} (FishUpdateRequest) - a partial update, only present fields change. */
export type FishUpdateRequest = Partial<FishCreateRequest>;
