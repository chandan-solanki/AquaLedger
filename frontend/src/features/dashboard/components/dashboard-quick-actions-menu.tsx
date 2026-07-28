"use client";

import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Building2,
  ChevronDown,
  Plus,
  Route as RouteIcon,
  ShoppingCart,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { memo } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePermissions } from "@/features/auth/hooks/use-permissions";

const QUICK_ACTIONS = [
  { key: "new-company", label: "New Company", href: "/companies/new", icon: Building2, permission: "company:create" },
  { key: "new-trip", label: "New Trip", href: "/trips/new", icon: RouteIcon, permission: "trip:create" },
  { key: "new-invoice", label: "New Invoice", href: "/invoices/new", icon: Wallet, permission: "invoice:create" },
  {
    key: "new-payment",
    label: "New Customer Payment",
    href: "/payments/new",
    icon: ArrowDownToLine,
    permission: "payment:create",
  },
  {
    key: "new-purchase-bill",
    label: "New Purchase Bill",
    href: "/purchase-bills/new",
    icon: ShoppingCart,
    permission: "purchase:create",
  },
  {
    key: "new-supplier-payment",
    label: "New Supplier Payment",
    href: "/supplier-payments/new",
    icon: ArrowUpFromLine,
    permission: "supplier_payment:create",
  },
] as const;

/**
 * The Dashboard header's Quick Actions dropdown, per TASKS.md Sprint 10
 * Session 2's "HEADER" spec. Each destination is permission-gated on the
 * same create-permission code its own module's Primary CTA uses (e.g.
 * `trip-list-page.tsx`'s "New Trip" button gates on `trip:create`), so this
 * menu never offers a shortcut the user couldn't also reach directly.
 * Sprint 10 Session 5 QA added the purchase bill/supplier payment entries
 * to restore parity with the buy-side KPIs and widgets already on the page
 * (Supplier Payments Today, Top Suppliers) - the original four covered only
 * the sell side.
 */
function DashboardQuickActionsMenuImpl() {
  const { hasPermission } = usePermissions();
  const visibleActions = QUICK_ACTIONS.filter((action) => hasPermission(action.permission));

  if (visibleActions.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus aria-hidden />
          Quick Actions
          <ChevronDown aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>Create new</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {visibleActions.map((action) => (
          <DropdownMenuItem key={action.key} asChild>
            <Link href={action.href}>
              <action.icon aria-hidden />
              <span>{action.label}</span>
            </Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export const DashboardQuickActionsMenu = memo(DashboardQuickActionsMenuImpl);
