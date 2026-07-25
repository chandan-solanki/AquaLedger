"use client";

import { LogOut, Palette, Settings, User } from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { getInitials } from "@/utils/get-initials";

// Profile / Notification Preferences / Appearance are placeholders this
// session (05_PAGE_CATALOG.md §14 builds the real pages) — only Logout is
// wired to real behavior.
function comingSoon(feature: string) {
  toast.info(`${feature} is coming soon.`);
}

export function UserMenu() {
  const user = useCurrentUser();
  const { logout } = useAuth();

  if (!user) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-9 gap-2 px-2">
          <Avatar size="sm">
            <AvatarFallback>{getInitials(user.fullName)}</AvatarFallback>
          </Avatar>
          <span className="hidden max-w-32 truncate text-sm font-medium md:inline">
            {user.fullName}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col">
          <span className="font-medium">{user.fullName}</span>
          <span className="truncate text-xs font-normal text-muted-foreground">{user.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => comingSoon("Profile")}>
          <User />
          <span>Profile</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => comingSoon("Notification preferences")}>
          <Settings />
          <span>Notification Preferences</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => comingSoon("Appearance settings")}>
          <Palette />
          <span>Appearance</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onClick={() => logout()}>
          <LogOut />
          <span>Log out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
