"use client";

import { ErrorState } from "@/components/feedback/error-state";
import { SettingsPageTemplate } from "@/components/templates/settings-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { CompanyProfileForm } from "@/features/company-profile/components/company-profile-form";
import { LogoUploader } from "@/features/company-profile/components/logo-uploader";
import { useCompanyProfile } from "@/features/company-profile/hooks/use-company-profile";
import { useDeleteCompanyLogo } from "@/features/company-profile/hooks/use-delete-company-logo";
import { useUpdateCompanyProfile } from "@/features/company-profile/hooks/use-update-company-profile";
import { useUploadCompanyLogo } from "@/features/company-profile/hooks/use-upload-company-logo";
import {
  toCompanyProfileFormValues,
  toCompanyProfileUpdatePayload,
  type CompanyProfileFormValues,
} from "@/features/company-profile/schemas/company-profile-form-schema";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

const SETTINGS_MANAGE_PERMISSION = "settings:manage";

export function CompanyProfilePage() {
  const { hasPermission } = usePermissions();
  const profileQuery = useCompanyProfile();
  const updateProfile = useUpdateCompanyProfile();
  const uploadLogo = useUploadCompanyLogo();
  const deleteLogo = useDeleteCompanyLogo();

  if (!hasPermission(SETTINGS_MANAGE_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to view the company profile"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = profileQuery.isError ? normalizeApiError(profileQuery.error) : null;

  async function handleSubmit(values: CompanyProfileFormValues) {
    await updateProfile.mutateAsync(toCompanyProfileUpdatePayload(values));
    toastSuccess("Company profile was updated.");
  }

  async function handleUploadLogo(file: File) {
    try {
      await uploadLogo.mutateAsync(file);
      toastSuccess("Logo uploaded.");
    } catch (error) {
      toastError(normalizeApiError(error).message);
    }
  }

  async function handleRemoveLogo() {
    try {
      await deleteLogo.mutateAsync();
      toastSuccess("Logo removed.");
    } catch (error) {
      toastError(normalizeApiError(error).message);
    }
  }

  const profile = profileQuery.data;
  // The backend returns a bare "/company-profile/logo" path (never a raw
  // storage key) - the browser must go through the BFF, not the FastAPI
  // origin directly (ARCHITECTURE.md §1.2), so this prefixes it the same
  // way every other feature's BFF route is reached.
  const logoSrc = profile?.logoUrl ? `/api${profile.logoUrl}` : null;

  return (
    <SettingsPageTemplate
      title="Company Profile"
      description="Your organization's identity, used throughout the app and on generated documents."
      isLoading={profileQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load company profile",
              description: apiError.message,
              onRetry: () => profileQuery.refetch(),
            }
          : null
      }
    >
      {profile && (
        <div className="space-y-8">
          <div>
            <h2 className="mb-3 text-sm font-medium text-foreground">Document Branding</h2>
            <LogoUploader
              logoUrl={logoSrc}
              onUpload={handleUploadLogo}
              onRemove={handleRemoveLogo}
              isUploading={uploadLogo.isPending}
              isRemoving={deleteLogo.isPending}
            />
          </div>

          <CompanyProfileForm
            defaultValues={toCompanyProfileFormValues(profile)}
            onSubmit={handleSubmit}
            disabled={updateProfile.isPending}
          />
        </div>
      )}
    </SettingsPageTemplate>
  );
}
