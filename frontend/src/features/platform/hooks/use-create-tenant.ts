"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { platformTenantKeys } from "@/features/platform/constants/query-keys";
import { platformTenantService } from "@/features/platform/services/tenant-service";
import type { TenantCreateRequest } from "@/features/platform/types/tenant";

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TenantCreateRequest) => platformTenantService.createTenant(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformTenantKeys.lists() });
    },
  });
}
