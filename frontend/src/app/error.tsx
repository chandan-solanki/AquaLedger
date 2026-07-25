"use client";

import { useEffect } from "react";
import Link from "next/link";
import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { toastInfo } from "@/lib/toast";

/**
 * The root error boundary — catches any render error not already handled
 * by a more specific boundary. Never exposes raw exception detail, per
 * `01_PRODUCT_VISION.md`'s API standard and `06_COMPONENT_LIBRARY.md` §14's
 * Server Error pattern: a generic, honest message plus Retry.
 */
export default function GlobalErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center">
      <div className="space-y-1.5">
        <h1 className="text-lg font-semibold">Something went wrong on our end</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Please try again. If the problem keeps happening, contact support with the reference
          below.
        </p>
        {error.digest && (
          <p className="font-mono text-xs text-muted-foreground">Reference: {error.digest}</p>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button onClick={reset}>
          <RotateCw />
          Retry
        </Button>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Refresh
        </Button>
        <Button variant="outline" asChild>
          <Link href="/">Go Home</Link>
        </Button>
        <Button
          variant="ghost"
          onClick={() => toastInfo("Contact support is coming soon.")}
        >
          Contact Support
        </Button>
      </div>
    </div>
  );
}
