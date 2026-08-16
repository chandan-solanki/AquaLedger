"use client";

import { Eye, Pencil } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { DeliveryChallan } from "@/features/delivery-challans/types/delivery-challan";

/**
 * Row-actions builder for the Delivery Challans list table - View and Edit.
 * Edit is only ever meaningful while the challan is `draft` - the backend
 * rejects it with 409 `DELIVERY_CHALLAN_NOT_DRAFT` otherwise, so it's hidden
 * for any other status; View has no such restriction, mirroring
 * `usePurchaseOrderRowActions`. RBAC-filtered via `hidden` against the
 * backend's actual `delivery_challan:view`/`delivery_challan:edit` codes -
 * cosmetic only, the real gate is the backend's own permission check on the
 * route.
 */
export function useDeliveryChallanRowActions(): (
  challan: DeliveryChallan
) => DataTableAction<DeliveryChallan>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (challan: DeliveryChallan) => {
      const isDraft = challan.status === "draft";
      return [
        {
          label: "View",
          icon: Eye,
          onClick: () => router.push(`/delivery-challans/${challan.id}`),
          hidden: () => !hasPermission("delivery_challan:view"),
        },
        {
          label: "Edit",
          icon: Pencil,
          onClick: () => router.push(`/delivery-challans/${challan.id}/edit`),
          hidden: () => !isDraft || !hasPermission("delivery_challan:edit"),
        },
      ];
    },
    [router, hasPermission]
  );
}
