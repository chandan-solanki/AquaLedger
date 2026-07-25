"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

import { cn } from "@/lib/utils";

function useIsOnline() {
  // Assume online until the browser tells us otherwise, so SSR/first paint
  // never flashes the offline bar.
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    setIsOnline(navigator.onLine);
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return isOnline;
}

/**
 * A persistent, low-key connectivity-lost indicator — deliberately not a
 * full-page blocking state, per `06_COMPONENT_LIBRARY.md` §13. Renders
 * nothing while online; mount once near the app shell so it's visible from
 * anywhere without every page wiring it up individually.
 */
export function OfflineState({ className }: { className?: string }) {
  const isOnline = useIsOnline();

  if (isOnline) return null;

  return (
    <div
      role="status"
      className={cn(
        "flex items-center justify-center gap-2 border-b bg-muted px-4 py-1.5 text-xs font-medium text-muted-foreground",
        className
      )}
    >
      <WifiOff className="size-3.5" aria-hidden />
      You&apos;re offline. Some actions are unavailable until your connection is restored.
    </div>
  );
}
