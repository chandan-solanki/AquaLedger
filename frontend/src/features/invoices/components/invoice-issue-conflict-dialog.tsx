"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { FISH_UNIT_LABELS } from "@/features/fish";
import { CATCH_GRADE_LABELS, tripCatchService, useFishOptions } from "@/features/trips";
import { INVOICE_STATUS_BADGE_VARIANT, INVOICE_STATUS_LABELS } from "@/features/invoices/constants/invoice-status";
import { useTripCatchConflicts } from "@/features/invoices/hooks/use-trip-catch-conflicts";
import type { ConflictingInvoice } from "@/features/invoices/types/trip-catch-conflict";
import { formatQuantity } from "@/utils/format-number";

export interface InvoiceIssueConflictDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The invoice that just failed to issue - excluded from its own conflict list. */
  currentInvoiceId: string;
  tripCatchId: string;
  /** `details.requested_quantity` off the 422 - the quantity that failed. */
  requiredQuantity: string;
}

const VISIBLE_CONFLICTS = 3;

function ConflictRow({ invoice, unitLabel, canView }: { invoice: ConflictingInvoice; unitLabel: string; canView: boolean }) {
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
 * Sprint 15 Session 6: shown instead of a generic "Insufficient inventory"
 * toast when issuing fails with 422 `INVOICE_INSUFFICIENT_INVENTORY`
 * (`InvoiceDetailPage`'s issue `onError`). Fetches the failing trip catch
 * (for its fish/grade identity, the same lookup `TripCatchSelectorField`
 * already does) and `GET /invoices/trip-catches/{id}/conflicts` (Session
 * 6) for the required/available/shortfall figures and any other invoice
 * that may explain the shortage - never a claim that a listed invoice
 * definitely caused it, only that it plausibly could have
 * (`conflictingInvoices` can never be proven causal, only correlated).
 *
 * Read-only throughout - no action here mutates the invoice, the trip
 * catch, or any other invoice. The user decides what to do next (edit the
 * item's quantity via the existing Edit action on this same page, or view
 * a competing invoice); nothing is silently adjusted.
 */
export function InvoiceIssueConflictDialog({
  open,
  onOpenChange,
  currentInvoiceId,
  tripCatchId,
  requiredQuantity,
}: InvoiceIssueConflictDialogProps) {
  const { hasPermission } = usePermissions();
  const [showAllConflicts, setShowAllConflicts] = useState(false);
  const fishOptions = useFishOptions();

  const tripCatchQuery = useQuery({
    queryKey: ["trip-catches", "detail", tripCatchId],
    queryFn: () => tripCatchService.getTripCatch(tripCatchId),
    enabled: Boolean(tripCatchId) && open,
    staleTime: 5 * 60 * 1000,
  });
  const conflictsQuery = useTripCatchConflicts(
    open ? tripCatchId : "",
    currentInvoiceId,
    requiredQuantity
  );

  const fish = tripCatchQuery.data ? fishOptions.fishById.get(tripCatchQuery.data.fishId) : undefined;
  const unitLabel = fish ? FISH_UNIT_LABELS[fish.unit] : "";
  const gradeLabel = tripCatchQuery.data?.grade ? CATCH_GRADE_LABELS[tripCatchQuery.data.grade] : "No grade";

  const isLoading = tripCatchQuery.isLoading || conflictsQuery.isLoading;
  const conflict = conflictsQuery.data;
  const conflicts = conflict?.conflictingInvoices ?? [];
  const hasNonDraftConflict = conflicts.some((c) => c.status !== "draft");
  const heading = hasNonDraftConflict
    ? "Other invoices referencing this catch"
    : "Other draft invoices referencing this catch";
  const visibleConflicts = showAllConflicts ? conflicts : conflicts.slice(0, VISIBLE_CONFLICTS);
  const hiddenCount = conflicts.length - visibleConflicts.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Unable to Issue Invoice</DialogTitle>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          Not enough stock is available for one or more invoice items.
        </p>

        {isLoading ? (
          <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden />
            Loading…
          </div>
        ) : (
          <div className="space-y-4">
            <p className="font-medium">
              {fish?.name ?? "Unknown fish"} — {gradeLabel}
            </p>

            <div className="space-y-1 rounded-lg border bg-muted/30 px-4 py-3 text-sm">
              <div className="flex items-center justify-between gap-6">
                <span className="text-muted-foreground">Required</span>
                <span className="font-semibold tabular-nums">
                  {formatQuantity(requiredQuantity)} {unitLabel}
                </span>
              </div>
              <div className="flex items-center justify-between gap-6">
                <span className="text-muted-foreground">Available</span>
                <span className="font-semibold tabular-nums">
                  {conflict ? formatQuantity(conflict.availableQuantity) : "—"} {unitLabel}
                </span>
              </div>
              <div className="flex items-center justify-between gap-6">
                <span className="text-muted-foreground">Shortfall</span>
                <span className="font-semibold text-destructive tabular-nums">
                  {conflict?.shortfallQuantity ? formatQuantity(conflict.shortfallQuantity) : "—"} {unitLabel}
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium">{heading}</p>
              {conflicts.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No other invoice could be identified as the cause. Stock may have changed due to
                  another operation.
                </p>
              ) : (
                <>
                  <ul className="space-y-2">
                    {visibleConflicts.map((invoiceConflict) => (
                      <ConflictRow
                        key={invoiceConflict.invoiceId}
                        invoice={invoiceConflict}
                        unitLabel={unitLabel}
                        canView={hasPermission("invoice:view")}
                      />
                    ))}
                  </ul>
                  {conflicts.length > VISIBLE_CONFLICTS && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-1"
                      onClick={() => setShowAllConflicts((prev) => !prev)}
                    >
                      {showAllConflicts ? "Show fewer" : `Show ${hiddenCount} more`}
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
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
