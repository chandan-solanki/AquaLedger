import { ErrorState } from "@/components/feedback/error-state";

export interface DataTableErrorProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

/**
 * The Data Table's Error State — a table-scoped failure (the list query
 * failed), never exposing raw internal exception detail, per
 * `06_COMPONENT_LIBRARY.md` §14 and `01_PRODUCT_VISION.md`'s API standard.
 * Composes the shared `ErrorState` primitive; `onRetry`, when provided,
 * re-invokes the exact failed query.
 */
export function DataTableError({
  title = "Couldn't load this table",
  description,
  onRetry,
  className,
}: DataTableErrorProps) {
  return <ErrorState title={title} description={description} onRetry={onRetry} className={className} />;
}
