import type { LucideIcon } from "lucide-react";
import {
  Anchor,
  ArrowDownToLine,
  ArrowUpFromLine,
  BarChart3,
  Building2,
  ClipboardList,
  Database,
  FileText,
  Fish,
  FolderOpen,
  Hash,
  History,
  Hourglass,
  KeyRound,
  LayoutDashboard,
  PackageCheck,
  Route,
  Scale,
  Settings,
  Shield,
  Ship,
  TrendingUp,
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
      {
        id: "fish-stock",
        title: "Fish Stock",
        icon: Fish,
        href: "/fish-stock",
        permission: "fish:view",
      },
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
        id: "delivery-challans",
        title: "Delivery Challans",
        icon: PackageCheck,
        href: "/delivery-challans",
        singular: "Delivery Challan",
        permission: "delivery_challan:view",
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
        id: "purchase-orders",
        title: "Purchase Orders",
        icon: ClipboardList,
        href: "/purchase-orders",
        singular: "Purchase Order",
        permission: "purchase_order:view",
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
    children: [
      {
        id: "reports-customer-ledger",
        title: "Customer Ledger",
        icon: ArrowDownToLine,
        href: "/reports/customer-ledger",
        permission: "reports:view",
      },
      {
        id: "reports-supplier-ledger",
        title: "Supplier Ledger",
        icon: ArrowUpFromLine,
        href: "/reports/supplier-ledger",
        permission: "reports:view",
      },
      {
        id: "reports-sales",
        title: "Sales Report",
        icon: FileText,
        href: "/reports/sales",
        permission: "reports:view",
      },
      {
        id: "reports-purchases",
        title: "Purchase Report",
        icon: FileText,
        href: "/reports/purchases",
        permission: "reports:view",
      },
      {
        id: "reports-outstanding",
        title: "Outstanding Report",
        icon: Scale,
        href: "/reports/outstanding",
        permission: "reports:view",
      },
      {
        id: "reports-aging",
        title: "Aging Report",
        icon: Hourglass,
        href: "/reports/aging",
        permission: "reports:view",
      },
      {
        id: "reports-trip-profitability",
        title: "Trip Profitability",
        icon: TrendingUp,
        href: "/reports/trip-profitability",
        permission: "reports:view",
      },
      {
        id: "reports-boat-profitability",
        title: "Boat Profitability",
        icon: Ship,
        href: "/reports/boat-profitability",
        permission: "reports:view",
      },
      {
        id: "reports-fish-sales",
        title: "Fish Sales Analytics",
        icon: Fish,
        href: "/reports/fish-sales",
        permission: "reports:view",
      },
      {
        id: "documents",
        title: "Document Center",
        icon: FolderOpen,
        href: "/documents",
        permission: "document:view",
      },
    ],
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
    ],
  },
];
