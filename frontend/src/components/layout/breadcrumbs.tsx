"use client";

import { Fragment } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { NAVIGATION, type NavItem } from "@/config/navigation";

interface Crumb {
  title: string;
  href: string;
}

const ACTION_SEGMENT_LABELS: Record<string, string> = {
  edit: "Edit",
};

function findNavPath(pathname: string, items: NavItem[], trail: NavItem[] = []): NavItem[] | null {
  for (const item of items) {
    const nextTrail = [...trail, item];

    if (item.href && (pathname === item.href || pathname.startsWith(`${item.href}/`))) {
      return nextTrail;
    }

    if (item.children) {
      const found = findNavPath(pathname, item.children, nextTrail);
      if (found) return found;
    }
  }

  return null;
}

/**
 * Auto-generates the breadcrumb chain from the current URL against the
 * static navigation config, per 03_INFORMATION_ARCHITECTURE.md §7: Dashboard
 * is always the root; sidebar group names (Masters, Finance, ...) are never
 * shown, only the module and record; `new`/`edit` action segments resolve
 * to readable labels.
 *
 * A Detail page's dynamic {id} segment needs its entity's real name (never
 * a raw ID, per §7 rule 3) — that resolution belongs to the page itself
 * once business modules with data fetching exist (Sprint 4+); this
 * component makes no business API calls, so it renders nothing past a
 * matched module for routes it can't yet label.
 */
export function Breadcrumbs() {
  const pathname = usePathname();

  if (pathname === "/dashboard") {
    return null;
  }

  const navPath = findNavPath(pathname, NAVIGATION);
  if (!navPath || navPath.length === 0) {
    return null;
  }

  const matchedItem = navPath[navPath.length - 1];

  const remainder = matchedItem.href
    ? pathname
        .slice(matchedItem.href.length)
        .split("/")
        .filter(Boolean)
    : [];

  // Exactly on a List page (no segments beyond the module's own href) —
  // List pages never show a breadcrumb, per 03_INFORMATION_ARCHITECTURE.md §7.
  if (remainder.length === 0) {
    return null;
  }

  const crumbs: Crumb[] = [
    { title: "Dashboard", href: "/dashboard" },
    ...navPath
      .filter((item): item is NavItem & { href: string } => Boolean(item.href))
      .map((item) => ({ title: item.title, href: item.href })),
  ];

  let runningHref = matchedItem.href ?? "";
  for (const segment of remainder) {
    runningHref += `/${segment}`;
    const title =
      segment === "new" && matchedItem.singular
        ? `New ${matchedItem.singular}`
        : (ACTION_SEGMENT_LABELS[segment] ?? segment);
    crumbs.push({ title, href: runningHref });
  }

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          return (
            <Fragment key={crumb.href}>
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{crumb.title}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link href={crumb.href}>{crumb.title}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {!isLast && <BreadcrumbSeparator />}
            </Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
