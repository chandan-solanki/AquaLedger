import { useMemo } from "react";

import { useAuth } from "@/features/auth/hooks/use-auth";
import { hasAllPermissions, hasAnyPermission, hasPermission } from "@/utils/permissions";

export function usePermissions() {
  const { user, permissions } = useAuth();
  const isSuperuser = user?.isSuperuser ?? false;

  return useMemo(
    () => ({
      permissions,
      hasPermission: (code: string) => hasPermission(permissions, code, isSuperuser),
      hasAnyPermission: (codes: string[]) => hasAnyPermission(permissions, codes, isSuperuser),
      hasAllPermissions: (codes: string[]) => hasAllPermissions(permissions, codes, isSuperuser),
    }),
    [permissions, isSuperuser]
  );
}
