"use client";

import type { ChangeEvent } from "react";

import { ImageIcon, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toastError } from "@/lib/toast";

// Mirrors the backend's exact allowlist/cap (app/modules/company_profile/
// constants.py) - duplicated rather than shared across the FE/BE boundary,
// the same convention every other cross-boundary validation rule in this
// codebase already follows (e.g. GSTIN/phone/email patterns). The backend
// remains authoritative regardless of what this pre-check allows through.
const ALLOWED_LOGO_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024;

export interface LogoUploaderProps {
  /** Resolved src for the current logo (already BFF-prefixed), or null when none is uploaded. */
  logoUrl: string | null;
  onUpload: (file: File) => Promise<void>;
  onRemove: () => Promise<void>;
  isUploading?: boolean;
  isRemoving?: boolean;
  disabled?: boolean;
}

/**
 * A logo isn't a person, so the preview deliberately does not reuse the
 * circular `Avatar` primitive - a plain bordered box sized for a header
 * logo's typical aspect ratio instead. The actual file input stays
 * visually hidden but reachable via its `<label>`-wrapped Button, so it
 * remains keyboard-operable and has a real accessible name - never a bare
 * `<div onClick>`.
 */
export function LogoUploader({
  logoUrl,
  onUpload,
  onRemove,
  isUploading = false,
  isRemoving = false,
  disabled = false,
}: LogoUploaderProps) {
  const busy = isUploading || isRemoving;

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!ALLOWED_LOGO_TYPES.includes(file.type)) {
      toastError("Logo must be a PNG, JPEG or WebP image.");
      return;
    }
    if (file.size > MAX_LOGO_SIZE_BYTES) {
      toastError("Logo must be 2 MB or smaller.");
      return;
    }

    void onUpload(file);
  }

  return (
    <div className="flex items-center gap-4">
      <div
        className={cn(
          "flex h-20 w-32 shrink-0 items-center justify-center rounded-md border border-dashed bg-muted/30",
          logoUrl && "border-solid bg-background"
        )}
      >
        {busy ? (
          <Loader2 className="size-5 animate-spin text-muted-foreground motion-reduce:animate-none" />
        ) : logoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- a same-origin BFF-proxied image, not an optimizable remote asset.
          <img src={logoUrl} alt="Company logo" className="h-full w-full object-contain p-1" />
        ) : (
          <ImageIcon aria-hidden="true" className="size-6 text-muted-foreground" />
        )}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <label htmlFor="company-logo-input">
            <Button type="button" variant="outline" size="sm" disabled={disabled || busy} asChild>
              <span>
                {isUploading && <Loader2 className="animate-spin motion-reduce:animate-none" />}
                {logoUrl ? "Change Logo" : "Upload Logo"}
              </span>
            </Button>
          </label>
          <input
            id="company-logo-input"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            disabled={disabled || busy}
            onChange={handleFileChange}
          />

          {logoUrl && (
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
