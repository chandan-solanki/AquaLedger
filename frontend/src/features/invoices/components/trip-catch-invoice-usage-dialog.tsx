"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { INVOICE_STATUS_BADGE_VARIANT, INVOICE_STATUS_LABELS } from "@/features/invoices/constants/invoice-status";
import { useTripCatchConflicts } from "@/features/invoices/hooks/use-trip-catch-conflicts";
import type { ConflictingInvoice } from "@/features/invoices/types/trip-catch-conflict";
import { formatQuantity } from "@/utils/format-number";

export interface TripCatchInvoiceUsageDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tripCatchId: string;
  unitLabel: string;
  /**
   * Sprint 15 Session 8: when this dialog is opened from the Invoice Detail
   * page's own "Other Invoice Usage" cell, pass that invoice's id so it is
   * excluded from its own conflict list - there is no such invoice when
   * opened from the Fish Stock page (Session 7), so this stays undefined
   * there and every invoice referencing the catch is shown.
   */
  currentInvoiceId?: string;
}

function InvoiceUsageRow({ invoice, unitLabel, canView }: { invoice: ConflictingInvoice; unitLabel: string; canView: boolean }) {
  const label = invoice.invoiceNumber ?? "Draft Invoice";
  return (
    <li className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm">
      <div className="space-y-0.5">
        <div className="flex items-center gap-2">
          <span className="font-medium">{label}</span>
          <Badge variant={INVOICE_STATUS_BADGE_VARIANT[invoice.status]}>
            {INVOICE_STATUS_LABELS[invoice.status]}
          </Badge>
        </div>
        <p className="text-muted-foreground">
          {invoice.companyName} · {formatQuantity(invoice.quantity)} {unitLabel}
        </p>
      </div>
      {canView ? (
        <Button variant="outline" size="sm" asChild>
          <Link href={`/invoices/${invoice.invoiceId}`}>View</Link>
        </Button>
      ) : null}
    </li>
  );
}

/**
 * Sprint 15 Session 7: "which invoices reference this catch" for the Fish
 * Stock detail page's Invoice Usage indicator - shown BEFORE any issue
 * attempt, purely for visibility (unlike `InvoiceIssueConflictDialog`, which
 * only appears after a failed issue). Reuses the same
 * `GET /invoices/trip-catches/{id}/conflicts` query (Session 6) with no
 * `required_quantity`/`exclude_invoice_id` - there is no "current invoice"
 * or "shortfall" on this page, only "who else references this catch."
 *
 * Only ever opened when the caller already has `invoice:view` (the trigger
 * that opens this dialog is itself permission-gated) - the internal check
 * here is defense in depth, the same posture `InvoiceIssueConflictDialog`
 * takes for its own View links.
 *
 * Sprint 15 Session 8: also reused, unmodified apart from the optional
 * `currentInvoiceId` prop, as the Invoice Detail page's own "Other invoices
 * referencing this catch" drill-down - the same Session 6 conflicts query,
 * just with that invoice's id passed as `excludeInvoiceId` so it never
 * appears as its own conflict.
 */
export function TripCatchInvoiceUsageDialog({
  open,
  onOpenChange,
  tripCatchId,
  unitLabel,
  currentInvoiceId,
}: TripCatchInvoiceUsageDialogProps) {
  const { hasPermission } = usePermissions();
  const conflictsQuery = useTripCatchConflicts(open ? tripCatchId : "", currentInvoiceId, undefined);
  const invoices = conflictsQuery.data?.conflictingInvoices ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Invoices referencing this catch</DialogTitle>
        </DialogHeader>

        {conflictsQuery.isLoading ? (
          <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden />
            Loading…
          </div>
        ) : invoices.length === 0 ? (
          <p className="text-sm text-muted-foreground">No invoices reference this catch.</p>
        ) : (
          <ul className="space-y-2">
            {invoices.map((invoice) => (
              <InvoiceUsageRow
                key={invoice.invoiceId}
                invoice={invoice}
                unitLabel={unitLabel}
                canView={hasPermission("invoice:view")}
              />
            ))}
          </ul>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
