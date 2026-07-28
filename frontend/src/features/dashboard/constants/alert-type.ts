import { AlertTriangle, Clock, ShieldAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { DashboardAlertType } from "@/features/dashboard/types/dashboard";

export const ALERT_TYPE_LABELS: Record<DashboardAlertType, string> = {
  boat_license_expiring: "Boat Licenses Expiring",
  boat_insurance_expiring: "Boat Insurance Expiring",
  invoice_overdue: "Invoices Overdue",
  purchase_bill_overdue: "Purchase Bills Overdue",
  draft_invoice_stale: "Stale Draft Invoices",
  draft_payment_stale: "Stale Draft Payments",
};

export const ALERT_TYPE_ICONS: Record<DashboardAlertType, LucideIcon> = {
  boat_license_expiring: ShieldAlert,
  boat_insurance_expiring: ShieldAlert,
  invoice_overdue: AlertTriangle,
  purchase_bill_overdue: AlertTriangle,
  draft_invoice_stale: Clock,
  draft_payment_stale: Clock,
};

export type DashboardAlertSeverity = "critical" | "advisory";

/**
 * Only two tiers, deliberately — `app/globals.css` defines no "warning"/
 * amber token yet (see `TrendMetricCard`'s own doc comment for the same
 * constraint), so severity styling stays within the existing destructive/
 * neutral tokens rather than inventing one. Overdue money (invoices,
 * purchase bills) is the financially urgent tier; expiring compliance dates
 * and stale drafts are advisory, not yet a problem.
 */
export const ALERT_TYPE_SEVERITY: Record<DashboardAlertType, DashboardAlertSeverity> = {
  boat_license_expiring: "advisory",
  boat_insurance_expiring: "advisory",
  invoice_overdue: "critical",
  purchase_bill_overdue: "critical",
  draft_invoice_stale: "advisory",
  draft_payment_stale: "advisory",
};
