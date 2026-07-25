"use client";

import { LoaderCircle } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** State the specific consequence plainly — never a generic "Are you sure?" (02_DESIGN_SYSTEM.md §2). */
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  /** "destructive" styles the confirm action with the Danger Button variant, per 06_COMPONENT_LIBRARY.md §8. */
  variant?: "default" | "destructive";
  isLoading?: boolean;
}

/**
 * The base Confirmation Dialog for any irreversible or hard-to-reverse
 * action (Issue, Post, Cancel, Remove Allocation), per
 * `06_COMPONENT_LIBRARY.md` §8 / `04_USER_FLOWS.md` §22. Built on Radix
 * AlertDialog rather than plain Dialog since a confirmation must be
 * explicitly acted on — no backdrop-click dismissal mid-decision.
 */
export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  variant = "default",
  isLoading = false,
}: ConfirmationDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={isLoading ? undefined : onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description && <AlertDialogDescription>{description}</AlertDialogDescription>}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction
            variant={variant === "destructive" ? "destructive" : "default"}
            disabled={isLoading}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
          >
            {isLoading && <LoaderCircle className="animate-spin motion-reduce:animate-none" aria-hidden />}
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
