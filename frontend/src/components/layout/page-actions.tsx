import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { LoaderCircle } from "lucide-react";

import { ActionBar } from "@/components/layout/action-bar";
import { Button } from "@/components/ui/button";

export interface PageAction {
  label: string;
  onClick?: () => void;
  href?: string;
  icon?: LucideIcon;
  disabled?: boolean;
  loading?: boolean;
}

interface PageActionsProps {
  /** Exactly one Primary Button per page — never two competing, per `06_COMPONENT_LIBRARY.md` §3. */
  primary?: PageAction;
  secondary?: PageAction[];
}

function ActionButton({ action, variant }: { action: PageAction; variant: "default" | "outline" }) {
  const Icon = action.loading ? LoaderCircle : action.icon;
  const content = (
    <>
      {Icon && (
        <Icon className={action.loading ? "animate-spin motion-reduce:animate-none" : undefined} aria-hidden />
      )}
      {action.label}
    </>
  );

  if (action.href) {
    return (
      <Button variant={variant} disabled={action.disabled || action.loading} asChild>
        <Link href={action.href}>{content}</Link>
      </Button>
    );
  }

  return (
    <Button variant={variant} disabled={action.disabled || action.loading} onClick={action.onClick}>
      {content}
    </Button>
  );
}

/**
 * The standardized "primary + supporting actions" row for a Page Header's
 * action slot, per `05_PAGE_CATALOG.md` §0 (Primary CTA top-right, styled
 * as Primary Button; Secondary CTAs as Outline buttons beside it) and
 * `02_DESIGN_SYSTEM.md` §8's Action Bar standard. Enforces the "exactly one
 * Primary Button" rule at the type level rather than leaving page authors
 * to assemble raw buttons by hand.
 */
export function PageActions({ primary, secondary }: PageActionsProps) {
  if (!primary && (!secondary || secondary.length === 0)) return null;

  return (
    <ActionBar>
      {secondary?.map((action) => (
        <ActionButton key={action.label} action={action} variant="outline" />
      ))}
      {primary && <ActionButton action={primary} variant="default" />}
    </ActionBar>
  );
}
