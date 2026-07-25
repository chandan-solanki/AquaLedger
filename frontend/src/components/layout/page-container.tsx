import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface PageContainerProps {
  children: ReactNode;
  className?: string;
  /** List pages are the deliberate full-width exception (06_COMPONENT_LIBRARY.md §1). */
  fullWidth?: boolean;
}

export function PageContainer({ children, className, fullWidth = false }: PageContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full space-y-6 p-4 md:p-6",
        !fullWidth && "max-w-6xl",
        className
      )}
    >
      {children}
    </div>
  );
}
