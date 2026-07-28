"use client";

import { useQuery } from "@tanstack/react-query";

import { supplierKeys } from "@/features/suppliers/constants/query-keys";
import { supplierService } from "@/features/suppliers/services/supplier-service";

/** A single supplier by id - disabled until an id is available. */
export function useSupplier(id: string | undefined) {
  return useQuery({
    queryKey: supplierKeys.detail(id ?? ""),
    queryFn: () => supplierService.getSupplier(id as string),
    enabled: Boolean(id),
  });
}
