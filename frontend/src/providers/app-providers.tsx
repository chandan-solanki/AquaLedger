"use client";

import { NuqsAdapter } from "nuqs/adapters/next/app";
import { Suspense, type ReactNode } from "react";

import { RouteProgressBar } from "@/components/layout/route-progress-bar";
import { AuthProvider } from "@/features/auth/context/auth-context";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";
import { ToastProvider } from "@/providers/toast-provider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <NuqsAdapter>
      <ThemeProvider>
        <QueryProvider>
          <AuthProvider>
            {/* `useSearchParams` (inside RouteProgressBar) requires its own Suspense boundary here,
                otherwise every route in the app - including statically-generated ones like
                /login - would be forced into fully dynamic rendering. */}
            <Suspense fallback={null}>
              <RouteProgressBar />
            </Suspense>
            {children}
            <ToastProvider />
          </AuthProvider>
        </QueryProvider>
      </ThemeProvider>
    </NuqsAdapter>
  );
}
