import { bffClient } from "@/lib/bff-client";
import type { ChangePasswordRequest, ProfileUpdateRequest } from "@/features/profile/types/profile";

/**
 * Talks only to the Next.js BFF's own routes (`/api/profile*`) - never the
 * FastAPI backend directly, mirroring `company-profile-service.ts`'s own
 * rationale exactly (ARCHITECTURE.md §1.2, §8.1).
 *
 * None of these return the updated profile: callers invalidate the auth
 * session query instead (`authKeys.session()`) so `useCurrentUser()` picks
 * up the fresh values through the one existing session source of truth,
 * rather than this service maintaining a second, parallel copy of the same
 * shape returned by `/auth/me`.
 */
export const profileService = {
  async updateProfile(payload: ProfileUpdateRequest): Promise<void> {
    await bffClient.put("/profile", payload);
  },

  async uploadAvatar(file: File): Promise<void> {
    const formData = new FormData();
    formData.append("file", file);
    // Overrides the client's default `Content-Type: application/json` for
    // this one request - same reason `company-profile-service.ts`'s
    // `uploadCompanyLogo` does, so the browser sets the multipart boundary.
    await bffClient.post("/profile/avatar", formData, {
      headers: { "Content-Type": undefined },
    });
  },

  async deleteAvatar(): Promise<void> {
    await bffClient.delete("/profile/avatar");
  },

  async changePassword(payload: ChangePasswordRequest): Promise<void> {
    await bffClient.post("/profile/change-password", payload);
  },
};
