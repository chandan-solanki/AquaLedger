"use client";

import { useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LifeBuoy } from "lucide-react";
import { toast } from "sonner";

import { SidebarBrand } from "@/components/layout/sidebar-brand";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { NAVIGATION, type NavItem } from "@/config/navigation";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { filterNavigation } from "@/utils/filter-navigation";

function isItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavGroup({ item, pathname }: { item: NavItem; pathname: string }) {
  const children = item.children ?? [item];
  const { isMobile, setOpenMobile } = useSidebar();

  return (
    <SidebarGroup>
      {item.children && <SidebarGroupLabel>{item.title}</SidebarGroupLabel>}
      <SidebarGroupContent>
        <SidebarMenu>
          {children.map((child) => (
            <SidebarMenuItem key={child.id}>
              <SidebarMenuButton asChild isActive={isItemActive(pathname, child.href!)} tooltip={child.title}>
                <Link
                  href={child.href!}
                  onClick={() => {
                    if (isMobile) setOpenMobile(false);
                  }}
                >
                  <child.icon />
                  <span>{child.title}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const { permissions, user } = useAuth();
  const isSuperuser = user?.isSuperuser ?? false;

  const items = useMemo(
    () => filterNavigation(NAVIGATION, permissions, isSuperuser),
    [permissions, isSuperuser]
  );

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarBrand />
      </SidebarHeader>
      <SidebarContent>
        {items.map((item) => (
          <NavGroup key={item.id} item={item} pathname={pathname} />
        ))}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip="Help & Support"
              onClick={() => toast.info("Help Center is coming soon.")}
            >
              <LifeBuoy />
              <span>Help & Support</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
