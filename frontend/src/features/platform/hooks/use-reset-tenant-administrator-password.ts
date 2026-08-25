"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { platformTenantAdministratorKeys } from "@/features/platform/constants/query-keys";
import { platformTenantAdministratorService } from "@/features/platform/services/tenant-administrator-service";

export interface ResetTenantAdministratorPasswordVariables {
  tenantId: string;
  userId: string;
  newPassword: string;
}

/**
 * No onError toast here, mirroring useResetUserPassword's own rationale —
 * a weak-password 422 needs to land on the dialog's own New Password field,
 * so ResetPasswordDialog (reused as-is from the users feature) owns its own
 * try/catch.
 */
export function useResetTenantAdministratorPassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ tenantId, userId, newPassword }: ResetTenantAdministratorPasswordVariables) =>
      platformTenantAdministratorService.resetPassword(tenantId, userId, newPassword),
    onSuccess: (_administrator, variables) => {
      queryClient.invalidateQueries({
        queryKey: platformTenantAdministratorKeys.list(variables.tenantId),
      });
    },
  });
}
