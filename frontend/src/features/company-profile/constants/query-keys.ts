/** A single-record resource - one tenant, one profile, no id/list variants. */
export const companyProfileKeys = {
  all: () => ["company-profile"] as const,
  detail: () => [...companyProfileKeys.all(), "detail"] as const,
};
