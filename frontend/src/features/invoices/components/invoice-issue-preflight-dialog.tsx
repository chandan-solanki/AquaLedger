"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Fish } from "@/features/fish";
import type { InvoiceIssuePreflightConflict } from "@/features/invoices/types/invoice-issue-preflight";
import type { InvoiceItem } from "@/features/invoices/types/invoice-item";
import { formatQuantity } from "@/utils/format-number";

export interface InvoiceIssuePreflightDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conflicts: InvoiceIssuePreflightConflict[];
  /** This invoice's own already-loaded items - resolves each conflict's fish name/unit without
   * any extra network call (Sprint 15 Session 10 §6/§8: "no unnecessary cross-module calls"). */
  items: InvoiceItem[];
  fishById: Map<string, Fish>;
  /** Proceeds to the existing Issue confirmation flow - this dialog never issues anything itself. */
  onContinueAnyway: () => void;
}

function ConflictRow({
  conflict,
  fishName,
  unitLabel,
}: {
  conflict: InvoiceIssuePreflightConflict;
  fishName: string;
  unitLabel: string;
}) {
  const hasOtherDraft = Number(conflict.otherDraftQuantity) > 0;
  return (
    <li className="space-y-1.5 rounded-md border px-3 py-2 text-sm">
      <p className="font-medium">{fishName}</p>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <p className="text-xs text-muted-foreground">Requested</p>
          <p className="font-semibold tabular-nums">
            {formatQuantity(conflict.requestedQuantity)} {unitLabel}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Available</p>
          <p className="font-semibold tabular-nums">
            {formatQuantity(conflict.availableQuantity)} {unitLabel}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Shortfall</p>
          <p className="font-semibold text-destructive tabular-nums">
            {formatQuantity(conflict.shortfallQuantity)} {unitLabel}
          </p>
        </div>
      </div>
      {hasOtherDraft && (
        <p className="text-xs text-muted-foreground">
          Also referenced by other draft invoices: {formatQuantity(conflict.otherDraftQuantity)}{" "}
          {unitLabel}
        </p>
      )}
    </li>
  );
}

/**
 * Sprint 15 Session 10: shown BEFORE the existing Issue confirmation, when
 * `GET /invoices/{id}/issue-preflight` finds one or more trip catches that
 * currently look insufficient - purely advisory visibility, never a hard
 * block. Deliberately a new, small component rather than a reuse of
 * `InvoiceIssueConflictDialog` (Session 6): that one is reactive, shown only
 * after a real 422 failure, keyed to one specific trip catch and its
 * competing invoices - materially different semantics from this session's
 * "check every affected catch before attempting to issue at all," which
 * needs a per-catch requested/available/shortfall summary this invoice's
 * own items produce, not another invoice's conflicting list.
 *
 * "Continue to Issue" does not issue anything itself - it only closes this
 * dialog and hands control back to the existing, unchanged Issue
 * confirmation dialog and mutation. The backend's own lock-protected
 * validation at actual issue time remains the sole authority; this dialog
 * exists only so the user isn't surprised by a 422 they could have
 * anticipated.
 */
export function InvoiceIssuePreflightDialog({
  open,
  onOpenChange,
  conflicts,
  items,
  fishById,
  onContinueAnyway,
}: InvoiceIssuePreflightDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Check stock before issuing</DialogTitle>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          Some invoice items may no longer have sufficient available stock.
        </p>

        <ul className="space-y-2">
          {conflicts.map((conflict) => {
            const item = items.find((candidate) => candidate.tripCatchId === conflict.tripCatchId);
            const fish = item ? fishById.get(item.fishId) : undefined;
            return (
              <ConflictRow
                key={conflict.tripCatchId}
                conflict={conflict}
                fishName={fish?.name ?? "Unknown fish"}
                unitLabel={item?.unit ?? ""}
              />
            );
          })}
        </ul>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onContinueAnyway}>Continue to Issue</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
