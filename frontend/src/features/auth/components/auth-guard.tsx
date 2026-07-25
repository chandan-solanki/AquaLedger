"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/features/auth/hooks/use-auth";

/**
 * The authoritative "must be logged in" check for the (authenticated) route
 * group (07_FRONTEND_ARCHITECTURE.md §4, §10) — backed by the session query,
 * which has already attempted a silent refresh by the time isLoading
 * resolves. middleware.ts's cookie-presence check is a fast pre-filter, not
 * a replacement for this.
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-svh w-full items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground motion-reduce:animate-none" aria-label="Loading" />
      </div>
    );
  }

  return <>{children}</>;
}
