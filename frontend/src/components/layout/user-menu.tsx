"use client";

import { useRouter } from "next/navigation";
import { LogOut, Palette, Settings, User } from "lucide-react";

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

// Every item below now navigates to a real page: Profile → /profile
// (Session 1), Notification Preferences → /profile/notifications
// (Session 4, an honest "nothing to configure yet" page - no notification
// delivery mechanism exists to have preferences over), Appearance →
// /profile/appearance (Session 5, a settings UI over the same next-themes
// mechanism the topbar's ThemeSwitcher already uses).

export function UserMenu() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const router = useRouter();

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
        <DropdownMenuItem onClick={() => router.push("/profile")}>
          <User />
          <span>Profile</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push("/profile/notifications")}>
          <Settings />
          <span>Notification Preferences</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push("/profile/appearance")}>
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
