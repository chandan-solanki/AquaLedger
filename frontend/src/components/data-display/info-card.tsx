import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface InfoCardProps {
  title?: string;
  description?: string;
  icon?: LucideIcon;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * A static, non-interactive card presenting reference or summary
 * information — a Detail page's Overview Card, a help/tips card, per
 * `06_COMPONENT_LIBRARY.md` §5's Information Card. The generic `Card`
 * primitive with a standardized title/icon/actions header, so every
 * Overview Card in the product shares one layout rather than each module
 * reassembling `CardHeader`/`CardTitle` by hand.
 */
export function InfoCard({ title, description, icon: Icon, actions, children, className }: InfoCardProps) {
  return (
    <Card className={cn(className)}>
      {(title || actions) && (
        <CardHeader className="flex-row items-start justify-between gap-2">
          <div className="flex items-start gap-2">
            {Icon && <Icon className="mt-0.5 size-4 text-muted-foreground" aria-hidden />}
            <div className="space-y-1">
              {title && <CardTitle className="text-sm">{title}</CardTitle>}
              {description && <p className="text-sm text-muted-foreground">{description}</p>}
            </div>
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </CardHeader>
      )}
      <CardContent>{children}</CardContent>
    </Card>
  );
}
