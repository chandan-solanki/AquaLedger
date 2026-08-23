"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { platformTenantKeys } from "@/features/platform/constants/query-keys";
import { platformTenantService } from "@/features/platform/services/tenant-service";
import { TENANT_STATUS_LABELS } from "@/features/platform/constants/tenant-status";
import type { TenantStatus } from "@/features/platform/types/tenant";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface UpdateTenantStatusVariables {
  id: string;
  status: TenantStatus;
}

/**
 * Owns the full status-change outcome (cache invalidation + toast) so every
 * call site behaves identically — mirrors useUpdateUserStatus's own
 * rationale. No navigation on success: the tenant still exists at the same
 * detail URL, just with a new status.
 */
export function useUpdateTenantStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status }: UpdateTenantStatusVariables) =>
      platformTenantService.updateTenantStatus(id, status),
    onSuccess: (tenant) => {
      queryClient.invalidateQueries({ queryKey: platformTenantKeys.lists() });
      queryClient.invalidateQueries({ queryKey: platformTenantKeys.detail(tenant.id) });
      toastSuccess(`${tenant.name} is now ${TENANT_STATUS_LABELS[tenant.status]}.`);
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
