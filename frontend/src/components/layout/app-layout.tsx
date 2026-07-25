import type { ReactNode } from "react";
import { cookies } from "next/headers";

import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

/**
 * The root authenticated shell: Sidebar + Header + scrollable content.
 * Reads the sidebar's persisted collapse-state cookie server-side (the
 * same cookie shadcn's Sidebar writes on toggle) so the correct state
 * renders on first paint — no expanded-then-collapsed flash on reload,
 * satisfying the "Remember Sidebar" rule in 03_INFORMATION_ARCHITECTURE.md §19.
 */
export async function AppLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();
  const defaultOpen = cookieStore.get("sidebar_state")?.value !== "false";

  return (
    <SidebarProvider defaultOpen={defaultOpen}>
      <AppSidebar />
      <SidebarInset className="h-svh overflow-hidden">
        <AppHeader />
        <div className="flex-1 overflow-y-auto">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
