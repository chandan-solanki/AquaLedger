/** Mirrors the backend's SupplierStatus enum (app/modules/suppliers/constants.py). */
export type SupplierStatus = "active" | "inactive";

/**
 * Raw backend shape (snake_case), matching SupplierResponse
 * (app/modules/suppliers/schemas.py) exactly. Money fields are strings - the
 * backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1). Unlike `Company`, there is no `company_type`
 * (Supplier is always a supplier), no `pan`/`alt_phone`/`address_line2`/
 * `pincode`/`opening_balance_date`/`opening_balance_type`/`notes` - Supplier
 * carries a smaller, flatter field set than Company.
 */
export interface BackendSupplier {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  legal_name: string | null;
  gstin: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  contact_person: string | null;
  credit_days: number;
  opening_balance: string;
  outstanding_amount: string;
  status: SupplierStatus;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every supplier-service.ts function returns. */
export interface Supplier {
  id: string;
  tenantId: string;
  code: string;
  name: string;
  legalName: string | null;
  gstin: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  contactPerson: string | null;
  creditDays: number;
  openingBalance: string;
  outstandingAmount: string;
  status: SupplierStatus;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendSupplier(supplier: BackendSupplier): Supplier {
  return {
    id: supplier.id,
    tenantId: supplier.tenant_id,
    code: supplier.code,
    name: supplier.name,
    legalName: supplier.legal_name,
    gstin: supplier.gstin,
    phone: supplier.phone,
    email: supplier.email,
    address: supplier.address,
    city: supplier.city,
    state: supplier.state,
    country: supplier.country,
    contactPerson: supplier.contact_person,
    creditDays: supplier.credit_days,
    openingBalance: supplier.opening_balance,
    outstandingAmount: supplier.outstanding_amount,
    status: supplier.status,
    createdAt: supplier.created_at,
    updatedAt: supplier.updated_at,
  };
}

/**
 * Query params for GET /suppliers (app/modules/suppliers/schemas.py's
 * SupplierListParams) - snake_case to match the wire format exactly, since
 * `supplier-service.ts` forwards these straight through as a query string.
 */
export interface SupplierListParams {
  q?: string;
  status?: SupplierStatus;
  city?: string;
  state?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /suppliers (SupplierCreateRequest,
 * app/modules/suppliers/schemas.py) - snake_case to match the wire format
 * exactly. Only `code` and `name` are required; every other field the
 * backend defaults or accepts as null when omitted. `outstanding_amount`/
 * `status` are never accepted here - the server always owns them
 * (outstanding_amount starts at 0, status always `active`).
 */
export interface SupplierCreateRequest {
  code: string;
  name: string;
  legal_name?: string;
  gstin?: string;
  phone?: string;
  email?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  contact_person?: string;
  credit_days?: number;
  opening_balance?: string;
}

/** Request body for PUT /suppliers/{id} (SupplierUpdateRequest) - a partial update, only present fields change. */
export type SupplierUpdateRequest = Partial<SupplierCreateRequest>;
