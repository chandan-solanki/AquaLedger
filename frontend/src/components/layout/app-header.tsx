"use client";

import { Bell, Search } from "lucide-react";
import { toast } from "sonner";

import { ThemeSwitcher } from "@/components/layout/theme-switcher";
import { UserMenu } from "@/components/layout/user-menu";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

// Breadcrumbs live in each page's own PageHeader, not here — per
// 06_COMPONENT_LIBRARY.md §1 (Top Navigation's contents: tenant identity,
// Global Search, theme toggle, Notification trigger, User Menu — no
// breadcrumb) and 02_DESIGN_SYSTEM.md §12 (breadcrumb sits with the page
// header, beneath the persistent topbar). Tenant-name display is deferred:
// GET /auth/me only returns tenant_id, no display name, until a tenant
// settings endpoint exists (Sprint 9) — same gap noted for the `Tenant`
// type in Session 2.
export function AppHeader() {
  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
      <SidebarTrigger />

      <div className="ml-auto flex items-center gap-1">
        <Button
          variant="ghost"
          className="hidden text-muted-foreground sm:inline-flex"
          onClick={() => toast.info("Global search is coming soon.")}
        >
          <Search />
          <span>Search…</span>
          <kbd className="ml-4 rounded border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">
            Ctrl K
          </kbd>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="sm:hidden"
          aria-label="Search"
          onClick={() => toast.info("Global search is coming soon.")}
        >
          <Search />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Notifications"
          onClick={() => toast.info("Notifications are coming soon.")}
        >
          <Bell />
        </Button>
        <ThemeSwitcher />
        <Separator orientation="vertical" className="mx-1 h-5" />
        <UserMenu />
      </div>
    </header>
  );
}
