"use client";

import { Clock, Mail, ShieldAlert, ShieldCheck, type LucideIcon } from "lucide-react";

import { FormSection } from "@/components/form";
import { SettingsPageTemplate } from "@/components/templates/settings-page-template";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { AvatarUploader } from "@/features/profile/components/avatar-uploader";
import { ChangePasswordForm } from "@/features/profile/components/change-password-form";
import { ProfileForm } from "@/features/profile/components/profile-form";
import { useChangePassword } from "@/features/profile/hooks/use-change-password";
import { useDeleteAvatar } from "@/features/profile/hooks/use-delete-avatar";
import { useUpdateProfile } from "@/features/profile/hooks/use-update-profile";
import { useUploadAvatar } from "@/features/profile/hooks/use-upload-avatar";
import {
  toChangePasswordPayload,
  type ChangePasswordFormValues,
} from "@/features/profile/schemas/password-form-schema";
import {
  toProfileFormValues,
  toProfileUpdatePayload,
  type ProfileFormValues,
} from "@/features/profile/schemas/profile-form-schema";
import { USER_STATUS_BADGE_VARIANT, USER_STATUS_LABELS } from "@/features/users/constants/user-status";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";

/**
 * All read/display data comes from the session already loaded by
 * AuthProvider (the same `/auth/me` data `useCurrentUser()`/`UserMenu`
 * use) — no separate profile fetch, so there's no distinct network-error
 * state here; AuthGuard already redirects to /login before this page
 * renders if the session itself is unusable. Mutations (edit fields,
 * avatar) invalidate that same session query on success (see the
 * use-*-profile/use-*-avatar hooks) rather than maintaining a second copy
 * of the user's data, so a save is reflected here AND in the header's
 * UserMenu without a page reload.
 */
export function ProfilePage() {
  const { user, isLoading } = useAuth();
  const updateProfile = useUpdateProfile();
  const uploadAvatar = useUploadAvatar();
  const deleteAvatar = useDeleteAvatar();
  const changePassword = useChangePassword();

  async function handleSubmit(values: ProfileFormValues) {
    await updateProfile.mutateAsync(toProfileUpdatePayload(values));
    toastSuccess("Profile was updated.");
  }

  async function handleUploadAvatar(file: File) {
    try {
      await uploadAvatar.mutateAsync(file);
      toastSuccess("Photo uploaded.");
    } catch (error) {
      toastError(normalizeApiError(error).message);
    }
  }

  async function handleRemoveAvatar() {
    try {
      await deleteAvatar.mutateAsync();
      toastSuccess("Photo removed.");
    } catch (error) {
      toastError(normalizeApiError(error).message);
    }
  }

  async function handleChangePassword(values: ChangePasswordFormValues) {
    await changePassword.mutateAsync(toChangePasswordPayload(values));
    // Accurate to what the backend actually does (AuthService.change_password
    // revokes every refresh token for this user, this session included) -
    // not an artificial logout, just an honest heads-up (Sprint 16 Session 3).
    toastSuccess("Password changed. You'll need to log in again on your other sessions.");
  }

  // The backend returns a bare "/profile/avatar" path (never a raw storage
  // key) - the browser must go through the BFF, not the FastAPI origin
  // directly (ARCHITECTURE.md §1.2), same convention CompanyProfilePage's
  // logoSrc already follows.
  const avatarSrc = user?.avatarUrl ? `/api${user.avatarUrl}` : null;

  return (
    <SettingsPageTemplate
      title="My Profile"
      description="Your account information, as it appears throughout the app."
      isLoading={isLoading}
    >
      {user && (
        <div className="space-y-8">
          <div className="flex items-center gap-4">
            <AvatarUploader
              avatarUrl={avatarSrc}
              fullName={user.fullName}
              onUpload={handleUploadAvatar}
              onRemove={handleRemoveAvatar}
              isUploading={uploadAvatar.isPending}
              isRemoving={deleteAvatar.isPending}
            />
            <div className="min-w-0">
              <h2 className="truncate text-lg font-medium text-foreground">{user.fullName}</h2>
              <p className="truncate text-sm text-muted-foreground">@{user.username}</p>
            </div>
            <Badge variant={USER_STATUS_BADGE_VARIANT[user.status]} className="ml-auto shrink-0">
              {USER_STATUS_LABELS[user.status]}
            </Badge>
          </div>

          <ProfileForm
            defaultValues={toProfileFormValues(user)}
            onSubmit={handleSubmit}
            disabled={updateProfile.isPending}
          />

          <dl className="grid gap-6 sm:grid-cols-2">
            <ProfileField icon={Mail} label="Email" value={user.email} />
            <ProfileField
              icon={ShieldCheck}
              label="Roles"
              value={user.roles.length > 0 ? user.roles.join(", ") : "No roles assigned"}
            />
            <ProfileField
              icon={Clock}
              label="Last login"
              value={user.lastLoginAt ? formatDateTime(user.lastLoginAt) : "Never"}
            />
          </dl>

          <FormSection
            title="Account Security"
            description="Change your password. This signs every other session out; this one ends once it next needs to refresh."
          >
            {user.mustChangePassword && (
              <Alert>
                <ShieldAlert />
                <AlertDescription>Your account requires a password change.</AlertDescription>
              </Alert>
            )}
            <ChangePasswordForm onSubmit={handleChangePassword} disabled={changePassword.isPending} />
          </FormSection>
        </div>
      )}
    </SettingsPageTemplate>
  );
}

function ProfileField({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Icon className="size-3.5" />
        {label}
      </dt>
      <dd className="mt-1 truncate text-sm text-foreground">{value}</dd>
    </div>
  );
}
