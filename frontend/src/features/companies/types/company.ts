/** Mirrors the backend's CompanyType enum (app/modules/companies/constants.py). */
export type CompanyType = "customer" | "supplier" | "both";

/** Mirrors the backend's CompanyStatus enum. */
export type CompanyStatus = "active" | "inactive";

/** Mirrors the backend's OpeningBalanceType enum. */
export type OpeningBalanceType = "debit" | "credit";

/**
 * Raw backend shape (snake_case), matching CompanyResponse
 * (app/modules/companies/schemas.py) exactly. Money fields are strings —
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number.
 */
export interface BackendCompany {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  legal_name: string | null;
  gstin: string | null;
  pan: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  state_code: string | null;
  pincode: string | null;
  country: string | null;
  phone: string | null;
  alt_phone: string | null;
  email: string | null;
  contact_person: string | null;
  company_type: CompanyType;
  credit_limit: string;
  credit_days: number;
  opening_balance: string;
  opening_balance_date: string | null;
  opening_balance_type: OpeningBalanceType | null;
  outstanding_amount: string;
  status: CompanyStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every company-service.ts function returns. */
export interface Company {
  id: string;
  tenantId: string;
  code: string;
  name: string;
  legalName: string | null;
  gstin: string | null;
  pan: string | null;
  addressLine1: string | null;
  addressLine2: string | null;
  city: string | null;
  state: string | null;
  stateCode: string | null;
  pincode: string | null;
  country: string | null;
  phone: string | null;
  altPhone: string | null;
  email: string | null;
  contactPerson: string | null;
  companyType: CompanyType;
  creditLimit: string;
  creditDays: number;
  openingBalance: string;
  openingBalanceDate: string | null;
  openingBalanceType: OpeningBalanceType | null;
  outstandingAmount: string;
  status: CompanyStatus;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendCompany(company: BackendCompany): Company {
  return {
    id: company.id,
    tenantId: company.tenant_id,
    code: company.code,
    name: company.name,
    legalName: company.legal_name,
    gstin: company.gstin,
    pan: company.pan,
    addressLine1: company.address_line1,
    addressLine2: company.address_line2,
    city: company.city,
    state: company.state,
    stateCode: company.state_code,
    pincode: company.pincode,
    country: company.country,
    phone: company.phone,
    altPhone: company.alt_phone,
    email: company.email,
    contactPerson: company.contact_person,
    companyType: company.company_type,
    creditLimit: company.credit_limit,
    creditDays: company.credit_days,
    openingBalance: company.opening_balance,
    openingBalanceDate: company.opening_balance_date,
    openingBalanceType: company.opening_balance_type,
    outstandingAmount: company.outstanding_amount,
    status: company.status,
    notes: company.notes,
    createdAt: company.created_at,
    updatedAt: company.updated_at,
  };
}

/**
 * Query params for GET /companies (app/modules/companies/schemas.py's
 * CompanyListParams) - snake_case to match the wire format exactly, since
 * `company-service.ts` forwards these straight through as a query string.
 */
export interface CompanyListParams {
  q?: string;
  company_type?: CompanyType;
  status?: CompanyStatus;
  city?: string;
  state?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /companies (CompanyCreateRequest,
 * app/modules/companies/schemas.py) - snake_case to match the wire format
 * exactly. Only `code`, `name` and `company_type` are required; every other
 * field the backend defaults or accepts as null when omitted.
 */
export interface CompanyCreateRequest {
  code: string;
  name: string;
  legal_name?: string;
  gstin?: string;
  pan?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  state_code?: string;
  pincode?: string;
  country?: string;
  phone?: string;
  alt_phone?: string;
  email?: string;
  contact_person?: string;
  company_type: CompanyType;
  credit_limit?: string;
  credit_days?: number;
  opening_balance?: string;
  opening_balance_date?: string;
  opening_balance_type?: OpeningBalanceType;
  status?: CompanyStatus;
  notes?: string;
}

/** Request body for PUT /companies/{id} (CompanyUpdateRequest) - a partial update, only present fields change. */
export type CompanyUpdateRequest = Partial<CompanyCreateRequest>;
