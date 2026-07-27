"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { boatKeys } from "@/features/boats/constants/query-keys";
import { boatService } from "@/features/boats/services/boat-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site — the Detail page's Delete action and the List page's row
 * action — gets identical behavior, mirroring `useDeleteFish`/
 * `useDeleteCompany` exactly. A call site that needs to react further (e.g.
 * closing its own confirmation dialog) passes an additional `onSuccess` to
 * `mutate()`/`mutateAsync()`, which TanStack Query runs alongside this
 * hook-level one.
 */
export function useDeleteBoat() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => boatService.deleteBoat(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: boatKeys.lists() });
      queryClient.removeQueries({ queryKey: boatKeys.detail(id) });
      toastSuccess("Boat deleted.");
      router.push("/boats");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
