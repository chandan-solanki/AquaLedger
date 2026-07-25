import { BellOff, History, SearchX, ShieldOff } from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { Button } from "@/components/ui/button";

/**
 * The shared "no matches" variant used across every List page's
 * Search/Filter and the Command Palette, distinct from a module's own
 * "No {Entity} yet" state, per `06_COMPONENT_LIBRARY.md` §13.
 */
export function NoSearchResults({ onClearFilters }: { onClearFilters?: () => void }) {
  return (
    <EmptyState
      icon={SearchX}
      title="No results found"
      description="Try adjusting your search or filters."
      action={
        onClearFilters && (
          <Button variant="outline" size="sm" onClick={onClearFilters}>
            Clear filters
          </Button>
        )
      }
    />
  );
}

/**
 * The "Coming Soon" variant for not-yet-shipped destinations (the Reports
 * module today), distinct from the standard no-data pattern in that it
 * communicates a roadmap state, per `06_COMPONENT_LIBRARY.md` §13.
 */
export function NoReports({ description }: { description?: string }) {
  return (
    <EmptyState
      icon={History}
      title="Reports are coming soon"
      description={description ?? "This report will be available once the module ships."}
    />
  );
}

/** An inline "you can't see this" placeholder for a permission-gated section within an otherwise-accessible page. */
export function NoPermission({ description }: { description?: string }) {
  return (
    <EmptyState
      icon={ShieldOff}
      title="You don't have access to this"
      description={description ?? "Ask an administrator if you believe this is a mistake."}
    />
  );
}

export function NoNotifications() {
  return (
    <EmptyState icon={BellOff} title="No notifications" description="You're all caught up." />
  );
}

export function NoActivity({ description }: { description?: string }) {
  return (
    <EmptyState
      icon={History}
      title="No recent activity"
      description={description ?? "Activity will appear here as it happens."}
    />
  );
}

/** Generic re-export for module List pages (Sprint 4+) to configure directly — see EmptyState's own doc comment. */
export function NoData({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return <EmptyState title={title} description={description} action={action} />;
}
