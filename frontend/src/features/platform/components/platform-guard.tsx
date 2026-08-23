"use client";

import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";

import { ErrorState } from "@/components/feedback/error-state";
import { useAuth } from "@/features/auth/hooks/use-auth";

/**
 * UX-level protection for the `/platform/*` route subtree, layered on top
 * of `AuthGuard` (which already guarantees the caller is authenticated by
 * the time this renders). Gates on `isPlatformAdmin` only — never
 * `isSuperuser`, a role name, or a permission code (Sprint 17's explicit
 * boundary). This is not the real security boundary: every `/platform/*`
 * BFF route re-checks with the real backend, which enforces
 * `require_platform_admin` independently of anything the client claims.
 *
 * Renders an inline `ErrorState` rather than redirecting - matching this
 * codebase's existing "no permission" pattern (e.g. CompanyDetailPage,
 * UserDetailPage) - so there is no redirect target to get wrong and no way
 * to create a redirect loop.
 */
export function PlatformGuard({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] w-full items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground motion-reduce:animate-none" aria-label="Loading" />
      </div>
    );
  }

  if (!user?.isPlatformAdmin) {
    return (
      <ErrorState
        title="You don't have access to Platform Administration"
        description="This area is restricted to platform administrators. Contact your platform administrator if you believe this is a mistake."
      />
    );
  }

  return <>{children}</>;
}
