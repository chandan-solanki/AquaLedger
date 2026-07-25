import type { LucideIcon } from "lucide-react";
import {
  Anchor,
  ArrowDownToLine,
  ArrowUpFromLine,
  BarChart3,
  Building2,
  Database,
  FileText,
  Fish,
  Hash,
  History,
  KeyRound,
  LayoutDashboard,
  Route,
  Settings,
  Shield,
  Ship,
  Tags,
  Truck,
  Users,
  Wallet,
} from "lucide-react";

/**
 * A permission of `string[]` means "visible if the user has ANY of these"
 * (e.g. Reports, gated by any report:* code) — a single `string` means
 * "visible only with this exact permission." Omitted entirely means
 * visible to every authenticated role (Dashboard only).
 */
export interface NavItem {
  id: string;
  title: string;
  icon: LucideIcon;
  href?: string;
  /** Singular form, e.g. "Company" for "Companies" — used for "New {singular}" breadcrumb/page labels (03_INFORMATION_ARCHITECTURE.md §18). Omitted for items with no Create route. */
  singular?: string;
  permission?: string | string[];
  children?: NavItem[];
}

/**
 * The application's primary navigation tree — one static source of truth
 * consumed by the Sidebar (and, later, Breadcrumbs/Command Palette).
 * Structure and permission codes per 03_INFORMATION_ARCHITECTURE.md §2–3
 * and the backend's actual resource:action permission set
 * (app/modules/auth/permissions.py).
 */
export const NAVIGATION: NavItem[] = [
  {
    id: "dashboard",
    title: "Dashboard",
    icon: LayoutDashboard,
    href: "/dashboard",
  },
  {
    id: "masters",
    title: "Masters",
    icon: Database,
    children: [
      {
        id: "companies",
        title: "Companies",
        icon: Building2,
        href: "/companies",
        singular: "Company",
        permission: "company:view",
      },
      {
        id: "suppliers",
        title: "Suppliers",
        icon: Truck,
        href: "/suppliers",
        singular: "Supplier",
        permission: "supplier:view",
      },
      { id: "fish", title: "Fish", icon: Fish, href: "/fish", singular: "Fish", permission: "fish:view" },
    ],
  },
  {
    id: "operations",
    title: "Operations",
    icon: Anchor,
    children: [
      { id: "boats", title: "Boats", icon: Ship, href: "/boats", singular: "Boat", permission: "boat:view" },
      { id: "trips", title: "Trips", icon: Route, href: "/trips", singular: "Trip", permission: "trip:view" },
    ],
  },
  {
    id: "finance",
    title: "Finance",
    icon: Wallet,
    children: [
      {
        id: "invoices",
        title: "Invoices",
        icon: FileText,
        href: "/invoices",
        singular: "Invoice",
        permission: "invoice:view",
      },
      {
        id: "customer-payments",
        title: "Customer Payments",
        icon: ArrowDownToLine,
        href: "/payments",
        singular: "Customer Payment",
        permission: "payment:view",
      },
      {
        id: "purchase-bills",
        title: "Purchase Bills",
        icon: FileText,
        href: "/purchase-bills",
        singular: "Purchase Bill",
        permission: "purchase:view",
      },
      {
        id: "supplier-payments",
        title: "Supplier Payments",
        icon: ArrowUpFromLine,
        href: "/supplier-payments",
        singular: "Supplier Payment",
        permission: "supplier_payment:view",
      },
    ],
  },
  {
    id: "reports",
    title: "Reports",
    icon: BarChart3,
    href: "/reports",
    permission: ["report:sales", "report:profit", "report:outstanding"],
  },
  {
    id: "administration",
    title: "Administration",
    icon: Shield,
    children: [
      { id: "users", title: "Users", icon: Users, href: "/users", singular: "User", permission: "user:manage" },
      {
        id: "roles",
        title: "Roles & Permissions",
        icon: KeyRound,
        href: "/roles",
        singular: "Role",
        permission: "user:manage",
      },
      { id: "audit-logs", title: "Audit Logs", icon: History, href: "/audit-logs", permission: "audit_log:view" },
    ],
  },
  {
    id: "settings",
    title: "Settings",
    icon: Settings,
    children: [
      {
        id: "settings-company",
        title: "Company Profile",
        icon: Building2,
        href: "/settings/company",
        permission: "settings:manage",
      },
      {
        id: "settings-sequences",
        title: "Numbering Sequences",
        icon: Hash,
        href: "/settings/sequences",
        permission: "settings:manage",
      },
      {
        id: "settings-categories",
        title: "Categories",
        icon: Tags,
        href: "/settings/categories",
        permission: "settings:manage",
      },
    ],
  },
];
