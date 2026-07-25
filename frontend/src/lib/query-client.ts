import { QueryClient, isServer } from "@tanstack/react-query";

import type { ApiError } from "@/types/api";

const RETRYABLE_CATEGORIES = new Set<ApiError["category"]>(["network", "server"]);
const MAX_QUERY_RETRIES = 2;

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30 * 1000,
        retry: (failureCount, error) => {
          const apiError = error as Partial<ApiError>;
          if (!apiError.category || !RETRYABLE_CATEGORIES.has(apiError.category)) {
            return false;
          }
          return failureCount < MAX_QUERY_RETRIES;
        },
      },
      mutations: {
        // Financial writes (Save, Issue, Post, Allocate) never auto-retry —
        // a failed mutation always surfaces to the user as an explicit,
        // user-initiated retry action (07_FRONTEND_ARCHITECTURE.md §8).
        retry: false,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

export function getQueryClient() {
  if (isServer) {
    return makeQueryClient();
  }

  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }

  return browserQueryClient;
}
