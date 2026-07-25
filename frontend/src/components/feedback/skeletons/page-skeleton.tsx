import { CardSkeleton } from "@/components/feedback/skeletons/card-skeleton";
import { DashboardSkeleton } from "@/components/feedback/skeletons/dashboard-skeleton";
import { FormSkeleton } from "@/components/feedback/skeletons/form-skeleton";
import { TableSkeleton } from "@/components/feedback/skeletons/table-skeleton";
import { Skeleton } from "@/components/ui/skeleton";

type PageSkeletonVariant = "list" | "form" | "detail" | "dashboard";

interface PageSkeletonProps {
  variant?: PageSkeletonVariant;
}

function PageTitleSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-4 w-40" />
      <div className="flex items-center justify-between gap-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-9 w-28" />
      </div>
    </div>
  );
}

/**
 * The composite skeleton for an entire page's initial load, assembled from
 * section-specific skeletons rather than a single generic placeholder, per
 * `06_COMPONENT_LIBRARY.md` §12. `variant` mirrors the page type templates
 * in `05_PAGE_CATALOG.md` §0 — List (Toolbar + Table), Form (field layout),
 * Detail (Overview Card + related sections), Dashboard (its own composite).
 */
export function PageSkeleton({ variant = "list" }: PageSkeletonProps) {
  if (variant === "dashboard") {
    return <DashboardSkeleton />;
  }

  if (variant === "form") {
    return (
      <div className="mx-auto w-full max-w-3xl space-y-6" aria-hidden>
        <PageTitleSkeleton />
        <FormSkeleton />
      </div>
    );
  }

  if (variant === "detail") {
    return (
      <div className="space-y-6" aria-hidden>
        <PageTitleSkeleton />
        <CardSkeleton lines={4} />
        <CardSkeleton lines={3} />
      </div>
    );
  }

  return (
    <div className="space-y-6" aria-hidden>
      <PageTitleSkeleton />
      <TableSkeleton />
    </div>
  );
}
