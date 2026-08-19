"use client";

import { Ban, CircleCheck, Eye, Pencil } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import type { ManagedUser } from "@/features/users/types/user";

const USER_MANAGE_PERMISSION = "user:manage";

/**
 * Row-actions builder for the Users list table. View/Edit navigate;
 * Activate/Deactivate hands the row's user to the caller rather than
 * mutating directly - the owning list page renders the one shared
 * confirmation dialog, mirroring useCompanyRowActions' Delete handoff.
 *
 * The Deactivate action is disabled (not hidden) on the caller's own row -
 * the backend rejects self-deactivation with CANNOT_DEACTIVATE_SELF
 * regardless, but disabling it here is a clearer signal than a failed
 * request. RBAC-filtered via `hidden`, per `07_FRONTEND_ARCHITECTURE.md`
 * §11 - cosmetic only, the real gate is the backend's own permission check.
 */
export function useUserRowActions(
  onStatusChangeRequest: (user: ManagedUser) => void
): (user: ManagedUser) => DataTableAction<ManagedUser>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const currentUser = useCurrentUser();

  return useCallback(
    (user: ManagedUser) => [
      {
        label: "View",
        icon: Eye,
        onClick: () => router.push(`/users/${user.id}`),
        hidden: () => !hasPermission(USER_MANAGE_PERMISSION),
      },
      {
        label: "Edit Role",
        icon: Pencil,
        onClick: () => router.push(`/users/${user.id}/edit`),
        hidden: () => !hasPermission(USER_MANAGE_PERMISSION),
      },
      {
        label: user.status === "inactive" ? "Activate" : "Deactivate",
        icon: user.status === "inactive" ? CircleCheck : Ban,
        variant: user.status === "inactive" ? "default" : "destructive",
        separatorBefore: true,
        onClick: () => onStatusChangeRequest(user),
        disabled: (row) => row.status !== "inactive" && row.id === currentUser?.id,
        hidden: () => !hasPermission(USER_MANAGE_PERMISSION),
      },
    ],
    [router, hasPermission, currentUser?.id, onStatusChangeRequest]
  );
}
