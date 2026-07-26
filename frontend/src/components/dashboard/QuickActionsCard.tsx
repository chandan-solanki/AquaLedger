"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface QuickAction {
  key: string;
  label: string;
  icon?: LucideIcon;
  onClick?: () => void;
  /** Renders as a `next/link` instead of a button when given. */
  href?: string;
}

export interface QuickActionsCardProps {
  title?: string;
  actions: QuickAction[];
  className?: string;
}

const ACTION_CLASS = cn(
  "flex flex-col items-center justify-center gap-1.5 rounded-lg border bg-card p-3 text-center transition-colors",
  "hover:bg-accent hover:text-accent-foreground",
  "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
);

/** The Dashboard's shortcut tile grid — each tile is a plain callback or a `next/link`, never an API call or route decision made by this component itself. */
export function QuickActionsCard({ title = "Quick Actions", actions, className }: QuickActionsCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {actions.map(({ key, label, icon: Icon, onClick, href }) => {
          const content = (
            <>
              {Icon && <Icon className="size-5" aria-hidden />}
              <span className="text-xs font-medium">{label}</span>
            </>
          );

          return href ? (
            <Link key={key} href={href} className={ACTION_CLASS}>
              {content}
            </Link>
          ) : (
            <button key={key} type="button" onClick={onClick} className={ACTION_CLASS}>
              {content}
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}
