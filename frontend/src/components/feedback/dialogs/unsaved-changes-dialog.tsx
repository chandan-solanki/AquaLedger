"use client";

import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";

export interface UnsavedChangesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called when the user chooses to leave anyway, discarding in-progress edits. */
  onDiscard: () => void;
}

/**
 * Shown when navigating away from a form with unsaved edits, per
 * `05_PAGE_CATALOG.md` §0's Form Page Template Cancel behavior ("a
 * lightweight 'discard changes?' confirmation only if the form has been
 * modified"). A future Form page wires this to its own dirty-state check
 * (react-hook-form's `formState.isDirty`) and router navigation guard —
 * not built here, since no form exists yet in this session's scope.
 */
export function UnsavedChangesDialog({ open, onOpenChange, onDiscard }: UnsavedChangesDialogProps) {
  return (
    <ConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Discard unsaved changes?"
      description="You have unsaved changes. If you leave this page, they will be lost."
      confirmLabel="Discard changes"
      cancelLabel="Keep editing"
      variant="destructive"
      onConfirm={onDiscard}
    />
  );
}
