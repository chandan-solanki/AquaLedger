"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { tripKeys } from "@/features/trips/constants/query-keys";
import { tripService } from "@/features/trips/services/trip-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site — the Detail page's Delete action and the List page's row
 * action — gets identical behavior, mirroring `useDeleteBoat` exactly. A
 * call site that needs to react further (e.g. closing its own confirmation
 * dialog) passes an additional `onSuccess` to `mutate()`/`mutateAsync()`,
 * which TanStack Query runs alongside this hook-level one.
 */
export function useDeleteTrip() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => tripService.deleteTrip(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: tripKeys.lists() });
      queryClient.removeQueries({ queryKey: tripKeys.detail(id) });
      toastSuccess("Trip deleted.");
      router.push("/trips");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
