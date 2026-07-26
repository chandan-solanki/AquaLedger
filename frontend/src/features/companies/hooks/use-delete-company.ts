"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { companyKeys } from "@/features/companies/constants/query-keys";
import { companyService } from "@/features/companies/services/company-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site — the Detail page's Delete action and the List page's row
 * action — gets identical behavior rather than each re-implementing it. A
 * call site that needs to react further (e.g. closing its own confirmation
 * dialog) passes an additional `onSuccess` to `mutate()`/`mutateAsync()`,
 * which TanStack Query runs alongside this hook-level one.
 */
export function useDeleteCompany() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => companyService.deleteCompany(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
      queryClient.removeQueries({ queryKey: companyKeys.detail(id) });
      toastSuccess("Company deleted.");
      router.push("/companies");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
