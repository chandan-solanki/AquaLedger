"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/features/auth/hooks/use-auth";

/**
 * Sprint 17 Session 5: a platform admin has no ordinary tenant permissions
 * (by design — Session 1's boundary is never relaxed just to make this
 * route work), so the tenant `/dashboard` is intentionally inaccessible to
 * them. Rather than let them hit that page's own Forbidden state, this
 * redirects them to their real landing page, `/platform/dashboard`, before
 * `DashboardPage` ever mounts (and before its `useDashboard()` query fires
 * a doomed request). Every other authenticated user renders the page
 * completely unaffected — this only ever redirects `isPlatformAdmin` users,
 * mirroring `PlatformGuard`'s own loading/decide shape in reverse.
 */
export function TenantDashboardGuard({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user?.isPlatformAdmin) {
      router.replace("/platform/dashboard");
    }
  }, [isLoading, user, router]);

  if (isLoading || user?.isPlatformAdmin) {
    return (
      <div className="flex min-h-[50vh] w-full items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground motion-reduce:animate-none" aria-label="Loading" />
      </div>
    );
  }

  return <>{children}</>;
}
