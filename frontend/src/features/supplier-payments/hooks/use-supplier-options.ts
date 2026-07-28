"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { supplierKeys, supplierService } from "@/features/suppliers";
import type { SupplierListParams } from "@/features/suppliers";

const SUPPLIER_OPTIONS_PARAMS: SupplierListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * All suppliers for this tenant, for the Supplier Payment list's Supplier
 * filter and for resolving `supplier_id` to a display name in the Supplier
 * column - `SupplierPaymentResponse` carries only `supplier_id`
 * (app/modules/supplier_payments/schemas.py), never a nested supplier name,
 * so this resolves it client-side through the Suppliers feature's own
 * public surface (`@/features/suppliers`) rather than the backend joining
 * it server-side (modules never reach into another feature's internals
 * directly - `07_FRONTEND_ARCHITECTURE.md` §5), mirroring `useCompanyOptions`
 * exactly. Previously a local, minimal inline lookup (Sprint 9 Session 1,
 * back when no `suppliers` frontend feature existed yet) - retired in favor
 * of the real feature now that it exists.
 */
export function useSupplierOptions() {
  const query = useQuery({
    queryKey: supplierKeys.list(SUPPLIER_OPTIONS_PARAMS),
    queryFn: () => supplierService.listSuppliers(SUPPLIER_OPTIONS_PARAMS),
    staleTime: 5 * 60 * 1000,
  });

  const suppliers = query.data?.data;

  return useMemo(() => {
    const list = suppliers ?? [];
    return {
      options: list.map((supplier): ComboboxOption => ({ value: supplier.id, label: supplier.name })),
      nameById: new Map(list.map((supplier) => [supplier.id, supplier.name])),
      isLoading: query.isLoading,
    };
  }, [suppliers, query.isLoading]);
}
