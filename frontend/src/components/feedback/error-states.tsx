import { CircleAlert, GitCompare, Lock, ServerCrash, ShieldAlert, WifiOff } from "lucide-react";

import { ErrorState } from "@/components/feedback/error-state";

interface RetryableErrorProps {
  description?: string;
  onRetry?: () => void;
}

/** "Couldn't reach the server" — Retry offered, since the failure is plausibly transient (`06_COMPONENT_LIBRARY.md` §14). */
export function NetworkError({ description, onRetry }: RetryableErrorProps) {
  return (
    <ErrorState
      icon={WifiOff}
      title="Couldn't reach the server"
      description={description ?? "Check your connection and try again."}
      onRetry={onRetry}
    />
  );
}

/** A generic, honest 500 — never exposes raw internal exception detail (`01_PRODUCT_VISION.md` API standard). */
export function ServerError({ description, onRetry }: RetryableErrorProps) {
  return (
    <ErrorState
      icon={ServerCrash}
      title="Something went wrong on our end"
      description={description ?? "Please try again in a moment."}
      onRetry={onRetry}
    />
  );
}

/**
 * A page-level 401. Never offers Retry — an unauthenticated request will
 * fail identically again — per the category default in
 * `06_COMPONENT_LIBRARY.md` §14. The live session-expiry flow
 * (`features/auth/context/auth-context.tsx`) already redirects to `/login`
 * automatically; this component is for a standalone section that needs to
 * say the same thing in place.
 */
export function Unauthorized({ description }: { description?: string }) {
  return (
    <ErrorState
      icon={Lock}
      title="Sign in required"
      description={description ?? "Your session may have expired. Please log in again."}
    />
  );
}

/** 403 — the user is authenticated but lacks permission, per `04_USER_FLOWS.md` §2's Unauthorized state. Never offers Retry. */
export function Forbidden({ description }: { description?: string }) {
  return (
    <ErrorState
      icon={ShieldAlert}
      title="You don't have access to this page"
      description={description ?? "Contact an administrator if you believe this is a mistake."}
    />
  );
}

/**
 * 409 — a concurrent-state conflict (e.g. allocating against an invoice
 * another session just fully paid). Inline by default per
 * `06_COMPONENT_LIBRARY.md` §14; Retry re-attempts against refreshed data.
 */
export function Conflict({ description, onRetry }: RetryableErrorProps) {
  return (
    <ErrorState
      variant="inline"
      icon={GitCompare}
      title="This record changed since you loaded it"
      description={description ?? "Refresh to see the current state before retrying."}
      onRetry={onRetry}
      retryLabel="Refresh"
    />
  );
}

/** 422 — a non-field-specific validation summary; per-field errors render inline at the field itself, not here. */
export function ValidationError({ description, onRetry }: RetryableErrorProps) {
  return (
    <ErrorState
      variant="inline"
      icon={CircleAlert}
      title="Please fix the highlighted fields"
      description={description}
      onRetry={onRetry}
    />
  );
}
