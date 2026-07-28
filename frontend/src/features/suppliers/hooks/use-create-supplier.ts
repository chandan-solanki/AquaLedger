"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierKeys } from "@/features/suppliers/constants/query-keys";
import { supplierService } from "@/features/suppliers/services/supplier-service";
import type { SupplierCreateRequest } from "@/features/suppliers/types/supplier";

export function useCreateSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SupplierCreateRequest) => supplierService.createSupplier(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
    },
  });
}
