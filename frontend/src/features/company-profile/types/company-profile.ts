/**
 * Raw backend shape (snake_case), matching CompanyProfileResponse
 * (backend/app/modules/company_profile/schemas.py) exactly. This is the
 * organization's OWN identity (used to brand generated documents) - not
 * to be confused with `BackendCompany` (customer/supplier party records).
 */
export interface BackendCompanyProfile {
  id: string;
  tenant_id: string;
  legal_name: string;
  display_name: string | null;
  company_code: string | null;
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
  website: string | null;
  gstin: string | null;
  pan: string | null;
  /** Relative path to GET /api/company-profile/logo, or null if no logo is uploaded - never a raw storage key. */
  logo_url: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every company-profile-service.ts function returns. */
export interface CompanyProfile {
  id: string;
  tenantId: string;
  legalName: string;
  displayName: string | null;
  companyCode: string | null;
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
  website: string | null;
  gstin: string | null;
  pan: string | null;
  logoUrl: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendCompanyProfile(profile: BackendCompanyProfile): CompanyProfile {
  return {
    id: profile.id,
    tenantId: profile.tenant_id,
    legalName: profile.legal_name,
    displayName: profile.display_name,
    companyCode: profile.company_code,
    addressLine1: profile.address_line1,
    addressLine2: profile.address_line2,
    city: profile.city,
    state: profile.state,
    stateCode: profile.state_code,
    pincode: profile.pincode,
    country: profile.country,
    phone: profile.phone,
    altPhone: profile.alt_phone,
    email: profile.email,
    website: profile.website,
    gstin: profile.gstin,
    pan: profile.pan,
    logoUrl: profile.logo_url,
    createdAt: profile.created_at,
    updatedAt: profile.updated_at,
  };
}

/**
 * Request body for PUT /company-profile (CompanyProfileUpsertRequest) -
 * snake_case to match the wire format exactly. A single-row-per-tenant
 * resource has no separate Create/Update request shape - every field is
 * optional, only supplied fields change (backend applies `exclude_unset`).
 */
export interface CompanyProfileUpdateRequest {
  legal_name?: string;
  display_name?: string;
  company_code?: string;
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
  website?: string;
  gstin?: string;
  pan?: string;
}
