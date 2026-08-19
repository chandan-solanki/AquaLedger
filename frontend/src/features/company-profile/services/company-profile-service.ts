import { bffClient } from "@/lib/bff-client";
import type {
  BackendCompanyProfile,
  CompanyProfile,
  CompanyProfileUpdateRequest,
} from "@/features/company-profile/types/company-profile";
import { mapBackendCompanyProfile } from "@/features/company-profile/types/company-profile";

/**
 * Talks only to the Next.js BFF's own routes (`/api/company-profile*`) —
 * never the FastAPI backend directly, mirroring `company-service.ts`'s own
 * rationale exactly (ARCHITECTURE.md §1.2, §8.1).
 */
export const companyProfileService = {
  async getCompanyProfile(): Promise<CompanyProfile> {
    const { data } = await bffClient.get<BackendCompanyProfile>("/company-profile");
    return mapBackendCompanyProfile(data);
  },

  async updateCompanyProfile(payload: CompanyProfileUpdateRequest): Promise<CompanyProfile> {
    const { data } = await bffClient.put<BackendCompanyProfile>("/company-profile", payload);
    return mapBackendCompanyProfile(data);
  },

  async uploadCompanyLogo(file: File): Promise<CompanyProfile> {
    const formData = new FormData();
    formData.append("file", file);
    // Overrides the client's default `Content-Type: application/json` for
    // this one request - axios then lets the browser set the multipart
    // boundary itself from the FormData body, exactly the reason
    // `authenticatedBackendFormRequest` (the BFF-route leg) omits the
    // header too.
    const { data } = await bffClient.post<BackendCompanyProfile>("/company-profile/logo", formData, {
      headers: { "Content-Type": undefined },
    });
    return mapBackendCompanyProfile(data);
  },

  async deleteCompanyLogo(): Promise<void> {
    await bffClient.delete("/company-profile/logo");
  },
};
