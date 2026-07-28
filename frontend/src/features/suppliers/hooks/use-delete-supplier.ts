"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { supplierKeys } from "@/features/suppliers/constants/query-keys";
import { supplierService } from "@/features/suppliers/services/supplier-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site - the Detail page's Delete action and the List page's row
 * action - gets identical behavior, mirroring `useDeleteCompany` exactly.
 */
export function useDeleteSupplier() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => supplierService.deleteSupplier(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
      queryClient.removeQueries({ queryKey: supplierKeys.detail(id) });
      toastSuccess("Supplier deleted.");
      router.push("/suppliers");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
