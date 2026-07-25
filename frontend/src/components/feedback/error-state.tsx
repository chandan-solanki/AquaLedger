import type { LucideIcon } from "lucide-react";
import { AlertTriangle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  onRetry?: () => void;
  retryLabel?: string;
  /**
   * "page" — a centered block for a whole page/section failing to load.
   * "inline" — a compact Alert for a scoped, in-context failure (409/422),
   * per `06_COMPONENT_LIBRARY.md` §14.
   */
  variant?: "page" | "inline";
  className?: string;
}

/**
 * The generic Error State primitive (`06_COMPONENT_LIBRARY.md` §14): never
 * exposes raw internal exception detail, offers Retry only where the
 * failure is plausibly transient. `NetworkError`/`ServerError` etc. below
 * are fixed-copy configurations of this one component, not separate
 * implementations — the same reuse pattern as Status Badge (§7).
 */
export function ErrorState({
  icon: Icon = AlertTriangle,
  title,
  description,
  onRetry,
  retryLabel = "Retry",
  variant = "page",
  className,
}: ErrorStateProps) {
  if (variant === "inline") {
    return (
      <Alert variant="destructive" className={className}>
        <Icon />
        <AlertTitle>{title}</AlertTitle>
        {(description || onRetry) && (
          <AlertDescription>
            {description && <p>{description}</p>}
            {onRetry && (
              <Button variant="outline" size="sm" onClick={onRetry} className="mt-1">
                {retryLabel}
              </Button>
            )}
          </AlertDescription>
        )}
      </Alert>
    );
  }

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-3 py-12 text-center text-muted-foreground",
        className
      )}
    >
      <Icon className="size-9 text-destructive" aria-hidden />
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
