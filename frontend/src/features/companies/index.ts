export { CompanyListPage } from "@/features/companies/pages/company-list-page";
export { CompanyCreatePage } from "@/features/companies/pages/company-create-page";
export { CompanyEditPage } from "@/features/companies/pages/company-edit-page";
export { CompanyDetailPage } from "@/features/companies/pages/company-detail-page";

export { CompanyForm, type CompanyFormProps } from "@/features/companies/components/company-form";

export { useCompanies } from "@/features/companies/hooks/use-companies";
export { useCompanyFilters } from "@/features/companies/hooks/use-company-filters";
export { useCompany } from "@/features/companies/hooks/use-company";
export { useCreateCompany } from "@/features/companies/hooks/use-create-company";
export {
  useUpdateCompany,
  type UpdateCompanyVariables,
} from "@/features/companies/hooks/use-update-company";
export { useDeleteCompany } from "@/features/companies/hooks/use-delete-company";

export { companyService } from "@/features/companies/services/company-service";
export type { CompanyListResult } from "@/features/companies/services/company-service";

export type {
  BackendCompany,
  Company,
  CompanyCreateRequest,
  CompanyListParams,
  CompanyStatus,
  CompanyType,
  CompanyUpdateRequest,
  OpeningBalanceType,
} from "@/features/companies/types/company";
export { mapBackendCompany } from "@/features/companies/types/company";

export type {
  CompanyFilters,
  CompanySortDirection,
  CompanySortField,
} from "@/features/companies/schemas/company-filters";
export {
  COMPANY_SORT_DIRECTIONS,
  COMPANY_SORT_FIELDS,
  DEFAULT_COMPANY_FILTERS,
  toCompanyListParams,
} from "@/features/companies/schemas/company-filters";

export type { CompanyFormValues } from "@/features/companies/schemas/company-form-schema";
export {
  DEFAULT_COMPANY_FORM_VALUES,
  companyFormSchema,
  toCompanyFormValues,
  toCompanyRequestPayload,
  toCompanyUpdatePayload,
} from "@/features/companies/schemas/company-form-schema";

export {
  COMPANY_STATUS_BADGE_VARIANT,
  COMPANY_STATUS_LABELS,
  COMPANY_STATUS_OPTIONS,
  COMPANY_STATUS_VALUES,
} from "@/features/companies/constants/company-status";

export { COMPANY_TYPE_LABELS, COMPANY_TYPE_OPTIONS } from "@/features/companies/constants/company-type";

export { companyKeys } from "@/features/companies/constants/query-keys";
