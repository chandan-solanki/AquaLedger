"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { supplierKeys, supplierService } from "@/features/suppliers";
import type { SupplierListParams } from "@/features/suppliers";

const SUPPLIER_OPTIONS_PARAMS: SupplierListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * Every supplier for this tenant, for the Supplier Ledger's Supplier
 * selector - sourced from the Suppliers feature's own public surface
 * (`@/features/suppliers`), never another feature's internals. Mirrors
 * `useCustomerOptions` exactly, on the buy side.
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
