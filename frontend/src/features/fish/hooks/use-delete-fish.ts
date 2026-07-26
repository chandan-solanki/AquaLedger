"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { fishKeys } from "@/features/fish/constants/query-keys";
import { fishService } from "@/features/fish/services/fish-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site — the Detail page's Delete action and the List page's row
 * action — gets identical behavior, mirroring `useDeleteCompany` exactly. A
 * call site that needs to react further (e.g. closing its own confirmation
 * dialog) passes an additional `onSuccess` to `mutate()`/`mutateAsync()`,
 * which TanStack Query runs alongside this hook-level one.
 */
export function useDeleteFish() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => fishService.deleteFish(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: fishKeys.lists() });
      queryClient.removeQueries({ queryKey: fishKeys.detail(id) });
      toastSuccess("Fish record deleted.");
      router.push("/fish");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
