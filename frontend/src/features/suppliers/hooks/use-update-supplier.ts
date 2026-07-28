"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierKeys } from "@/features/suppliers/constants/query-keys";
import { supplierService } from "@/features/suppliers/services/supplier-service";
import type { SupplierUpdateRequest } from "@/features/suppliers/types/supplier";

export interface UpdateSupplierVariables {
  id: string;
  payload: SupplierUpdateRequest;
}

export function useUpdateSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateSupplierVariables) => supplierService.updateSupplier(id, payload),
    onSuccess: (supplier) => {
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
      queryClient.invalidateQueries({ queryKey: supplierKeys.detail(supplier.id) });
    },
  });
}
