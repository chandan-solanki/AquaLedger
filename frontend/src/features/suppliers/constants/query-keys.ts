import type { SupplierListParams } from "@/features/suppliers/types/supplier";

export const supplierKeys = {
  all: () => ["suppliers"] as const,
  lists: () => [...supplierKeys.all(), "list"] as const,
  list: (params: SupplierListParams) => [...supplierKeys.lists(), params] as const,
  details: () => [...supplierKeys.all(), "detail"] as const,
  detail: (id: string) => [...supplierKeys.details(), id] as const,
};
