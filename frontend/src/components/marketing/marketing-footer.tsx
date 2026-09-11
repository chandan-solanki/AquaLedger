import Link from "next/link";

import { SITE_NAME } from "@/lib/site-config";

export function MarketingFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t">
      <div className="mx-auto flex w-full max-w-5xl flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-muted-foreground sm:flex-row">
        <p>
          &copy; {year} {SITE_NAME}. All rights reserved.
        </p>
        <nav className="flex items-center gap-6" aria-label="Footer">
          <Link href="/" className="hover:text-foreground">
            Home
          </Link>
          <Link href="/privacy" className="hover:text-foreground">
            Privacy Policy
          </Link>
          <Link href="/login" className="hover:text-foreground">
            Sign in
          </Link>
        </nav>
      </div>
    </footer>
  );
}
