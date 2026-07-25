import Link from "next/link";
import { Fish } from "lucide-react";

export function SidebarBrand() {
  return (
    <Link
      href="/dashboard"
      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sidebar-foreground"
    >
      <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
        <Fish className="size-4" aria-hidden />
      </div>
      <span className="truncate text-sm font-semibold group-data-[collapsible=icon]:hidden">
        AquaLedger
      </span>
    </Link>
  );
}
