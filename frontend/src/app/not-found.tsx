import Link from "next/link";
import { FileQuestion } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * The route-level catch-all for any unmatched URL. Distinct from a future
 * Detail-page's "record not found" state (`04_USER_FLOWS.md` §19), which
 * will reuse `ErrorState` with entity-specific copy once Detail pages
 * exist — this file only covers "there is no route here at all."
 */
export default function NotFound() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center">
      <FileQuestion className="size-10 text-muted-foreground" aria-hidden />
      <div className="space-y-1.5">
        <h1 className="text-lg font-semibold">Page not found</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist or may have been moved.
        </p>
      </div>
      <Button asChild>
        <Link href="/">Go Home</Link>
      </Button>
    </div>
  );
}
