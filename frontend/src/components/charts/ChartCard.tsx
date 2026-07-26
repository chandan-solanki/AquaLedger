import type { ReactNode } from "react";

import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { ChartError } from "./ChartError";
import { ChartLoading } from "./ChartLoading";

export interface ChartCardProps {
  title: string;
  description?: string;
  /** e.g. an `ExportMenu` or a period toggle, rendered top-right of the header. */
  actions?: ReactNode;
  isLoading?: boolean;
  error?: string;
  onRetry?: () => void;
  height?: number;
  children: ReactNode;
  className?: string;
}

/**
 * The reusable card wrapper every chart/report widget renders inside —
 * title/description/actions header plus a body that swaps to `ChartLoading`/
 * `ChartError` based on props. Has no idea what its `children` chart is; the
 * individual `LineChart`/`BarChart`/etc. components also carry their own
 * loading/error/empty handling so they work the same way when used without
 * this wrapper.
 */
export function ChartCard({
  title,
  description,
  actions,
  isLoading,
  error,
  onRetry,
  height = 300,
  children,
  className,
}: ChartCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        {actions && <CardAction>{actions}</CardAction>}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ChartLoading height={height} />
        ) : error ? (
          <ChartError description={error} onRetry={onRetry} height={height} />
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
