"use client";

import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";

export interface DeleteConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The record's display name, e.g. "Acme Seafoods" — never a raw ID, per 02_DESIGN_SYSTEM.md's naming discipline. */
  entityName: string;
  /** What kind of record, e.g. "company" — used to build the default description. */
  entityLabel?: string;
  onConfirm: () => void;
  description?: string;
  isLoading?: boolean;
}

/**
 * The Delete Dialog variant of Confirmation Dialog, styled with the Danger
 * Button as its primary action, per `06_COMPONENT_LIBRARY.md` §8. Reserved
 * for genuinely reversible-in-effect records (draft records, unreferenced
 * masters) — issued/posted financial records are immutable and never
 * offered this dialog, per this project's append-only ledger rule.
 */
export function DeleteConfirmationDialog({
  open,
  onOpenChange,
  entityName,
  entityLabel = "record",
  onConfirm,
  description,
  isLoading = false,
}: DeleteConfirmationDialogProps) {
  return (
    <ConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Delete ${entityName}?`}
      description={description ?? `This will permanently remove this ${entityLabel}. This action cannot be undone.`}
      confirmLabel="Delete"
      variant="destructive"
      onConfirm={onConfirm}
      isLoading={isLoading}
    />
  );
}
