"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export interface SessionExpiredDialogProps {
  open: boolean;
  onLoginAgain: () => void;
}

/**
 * A blocking modal stating the session has expired, per `04_USER_FLOWS.md`
 * §2's Session Expiry flow. Not currently wired into
 * `features/auth/context/auth-context.tsx` — the live app already handles
 * expiry via an immediate toast + redirect to `/login`, which satisfies the
 * same flow. This component is available for a future session to adopt if
 * a blocking confirmation (rather than an auto-redirect) is preferred once
 * real forms exist and in-progress state needs to be visibly preserved
 * before navigating away.
 *
 * Non-dismissible by design (no close button, ignores outside-click/Escape)
 * — the session is genuinely gone, so there is nothing to "cancel" back to.
 */
export function SessionExpiredDialog({ open, onLoginAgain }: SessionExpiredDialogProps) {
  return (
    <Dialog open={open} onOpenChange={() => undefined}>
      <DialogContent showCloseButton={false} onEscapeKeyDown={(e) => e.preventDefault()} onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>Your session has expired</DialogTitle>
          <DialogDescription>Please log in again to continue where you left off.</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button onClick={onLoginAgain}>Log In Again</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
