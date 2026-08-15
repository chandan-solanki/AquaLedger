import { Badge } from "@/components/ui/badge";
import { RISK_LEVEL_LABELS, type RiskLevel } from "@/features/reports/constants/risk-level";
import { cn } from "@/lib/utils";

/**
 * The Outstanding/Aging Report's Risk Indicator (TASKS.md Sprint 11 Session
 * 3 Phase B: "Green/Yellow/Red"). The shared `Badge` primitive has no
 * dedicated success/warning variant (`02_DESIGN_SYSTEM.md`'s Status
 * System - the same constraint `INVOICE_STATUS_BADGE_VARIANT` documents),
 * so this is the one place in Reports that overrides Badge's color
 * directly via `className` rather than reusing one of its four variants -
 * a generic `secondary`/`outline` reading would lose the traffic-light
 * meaning the report explicitly calls for.
 */
const RISK_LEVEL_CLASSES: Record<RiskLevel, string> = {
  low: "border-transparent bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-400",
  medium:
    "border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-500/15 dark:text-yellow-400",
  high: "border-transparent bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-400",
};

interface RiskBadgeProps {
  level: RiskLevel;
  className?: string;
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  return (
    <Badge className={cn(RISK_LEVEL_CLASSES[level], className)}>{RISK_LEVEL_LABELS[level]}</Badge>
  );
}
