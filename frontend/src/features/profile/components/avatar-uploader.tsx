"use client";

import type { ChangeEvent } from "react";

import { Loader2 } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { toastError } from "@/lib/toast";
import { getInitials } from "@/utils/get-initials";

// Mirrors the backend's exact allowlist/cap (app/modules/profile/
// constants.py) - duplicated rather than shared across the FE/BE boundary,
// the same convention `LogoUploader` already follows for its own identical
// numbers. The backend remains authoritative regardless of what this
// pre-check allows through.
const ALLOWED_AVATAR_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024;

export interface AvatarUploaderProps {
  /** Resolved src for the current avatar (already BFF-prefixed), or null when none is uploaded. */
  avatarUrl: string | null;
  /** For the initials fallback when there's no avatar image. */
  fullName: string;
  onUpload: (file: File) => Promise<void>;
  onRemove: () => Promise<void>;
  isUploading?: boolean;
  isRemoving?: boolean;
  disabled?: boolean;
}

/**
 * A user's own photo, unlike a company logo, belongs in the circular
 * `Avatar` primitive with an initials fallback - deliberately not
 * `LogoUploader` (which just as deliberately avoids that primitive, since
 * a logo isn't a person). Same interaction skeleton as `LogoUploader`
 * otherwise: a visually-hidden file input reachable via a `<label>`-
 * wrapped Button, so it stays keyboard-operable with a real accessible
 * name - never a bare `<div onClick>`.
 */
export function AvatarUploader({
  avatarUrl,
  fullName,
  onUpload,
  onRemove,
  isUploading = false,
  isRemoving = false,
  disabled = false,
}: AvatarUploaderProps) {
  const busy = isUploading || isRemoving;

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
      toastError("Avatar must be a PNG, JPEG or WebP image.");
      return;
    }
    if (file.size > MAX_AVATAR_SIZE_BYTES) {
      toastError("Avatar must be 2 MB or smaller.");
      return;
    }

    void onUpload(file);
  }

  return (
    <div className="flex items-center gap-4">
      <Avatar size="lg">
        {busy ? (
          <AvatarFallback>
            <Loader2 className="size-5 animate-spin text-muted-foreground motion-reduce:animate-none" />
          </AvatarFallback>
        ) : (
          <>
            {avatarUrl && <AvatarImage src={avatarUrl} alt="Your avatar" />}
            <AvatarFallback>{getInitials(fullName)}</AvatarFallback>
          </>
        )}
      </Avatar>

      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <label htmlFor="profile-avatar-input">
            <Button type="button" variant="outline" size="sm" disabled={disabled || busy} asChild>
              <span>
                {isUploading && <Loader2 className="animate-spin motion-reduce:animate-none" />}
                {avatarUrl ? "Change Photo" : "Upload Photo"}
              </span>
            </Button>
          </label>
          <input
            id="profile-avatar-input"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            disabled={disabled || busy}
            onChange={handleFileChange}
          />

          {avatarUrl && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={disabled || busy}
              onClick={() => void onRemove()}
            >
              {isRemoving && <Loader2 className="animate-spin motion-reduce:animate-none" />}
              Remove
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">PNG, JPEG or WebP, up to 2 MB.</p>
      </div>
    </div>
  );
}
