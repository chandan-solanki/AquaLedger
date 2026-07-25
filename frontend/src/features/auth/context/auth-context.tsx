"use client";

import { createContext, useCallback, useEffect, useMemo, useRef, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { authKeys } from "@/features/auth/constants/query-keys";
import { authService } from "@/features/auth/services/auth-service";
import type { AuthState, LoginCredentials, Tenant, User } from "@/features/auth/types/auth";
import type { ApiError } from "@/types/api";

export interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  loginError: ApiError | null;
  isLoggingIn: boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Reacts to any query in the cache failing with an "unauthorized" ApiError
 * — not just the session query itself — by clearing the session and
 * bouncing to /login. This is what makes 401s from future business queries
 * (Sprint 3+, once they're wired through apiClient) trigger the same
 * Session Expired flow without each feature reimplementing it
 * (07_FRONTEND_ARCHITECTURE.md §10, §15).
 */
function useSessionExpiredWatcher(onExpired: () => void) {
  const queryClient = useQueryClient();
  const onExpiredRef = useRef(onExpired);
  onExpiredRef.current = onExpired;

  useEffect(() => {
    return queryClient.getQueryCache().subscribe((event) => {
      if (event.type !== "updated" || event.action.type !== "error") return;

      const { queryKey } = event.query;
      const isSessionQuery = queryKey[0] === "auth" && queryKey[1] === "session";
      if (isSessionQuery) return;

      const error = event.action.error as Partial<ApiError> | undefined;
      if (error?.category === "unauthorized") {
        onExpiredRef.current();
      }
    });
  }, [queryClient]);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const hasHandledExpiryRef = useRef(false);

  const sessionQuery = useQuery({
    queryKey: authKeys.session(),
    queryFn: async () => {
      const { user } = await authService.getSession();
      return user;
    },
    staleTime: 5 * 60 * 1000,
    // A missing session is expected for every anonymous visitor — never
    // noisy-retry it.
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: ({ user }) => {
      hasHandledExpiryRef.current = false;
      queryClient.setQueryData(authKeys.session(), user);
    },
  });

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const { user } = await loginMutation.mutateAsync(credentials);
      return user;
    },
    [loginMutation]
  );

  const logout = useCallback(async () => {
    await authService.logout().catch(() => undefined);
    queryClient.setQueryData(authKeys.session(), null);
    queryClient.clear();
    router.push("/login");
  }, [queryClient, router]);

  const refreshUser = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: authKeys.session() });
  }, [queryClient]);

  const handleSessionExpired = useCallback(() => {
    if (hasHandledExpiryRef.current) return;
    hasHandledExpiryRef.current = true;

    authService.logout().catch(() => undefined);
    queryClient.setQueryData(authKeys.session(), null);
    queryClient.clear();
    toast.error("Your session has expired. Please log in again.");
    router.push(`/login?next=${encodeURIComponent(pathname)}`);
  }, [queryClient, router, pathname]);

  useSessionExpiredWatcher(handleSessionExpired);

  const user = sessionQuery.data ?? null;

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      tenant: user ? ({ id: user.tenantId } satisfies Tenant) : null,
      permissions: user?.permissions ?? [],
      isAuthenticated: Boolean(user),
      isLoading: sessionQuery.isLoading,
      login,
      logout,
      refreshUser,
      loginError: (loginMutation.error as ApiError | null) ?? null,
      isLoggingIn: loginMutation.isPending,
    }),
    [
      user,
      sessionQuery.isLoading,
      login,
      logout,
      refreshUser,
      loginMutation.error,
      loginMutation.isPending,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
