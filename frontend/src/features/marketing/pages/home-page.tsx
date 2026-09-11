import Link from "next/link";
import {
  Anchor,
  Banknote,
  Building2,
  FileText,
  Fish as FishIcon,
  Receipt,
  ShieldCheck,
  Ship,
  Truck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { SITE_NAME } from "@/lib/site-config";

const capabilities = [
  {
    icon: Building2,
    title: "Companies",
    description:
      "A customer master with credit terms, GST details, and a running outstanding balance for every business you trade with.",
  },
  {
    icon: FishIcon,
    title: "Fish master data",
    description: "A shared catalog of fish, categories, units, and tax rates used across every trade.",
  },
  {
    icon: Ship,
    title: "Boats & trips",
    description:
      "A boat registry plus trip records that track catches by grade and the expenses incurred on each trip.",
  },
  {
    icon: Receipt,
    title: "Invoices",
    description: "Sales invoices with line-item tax calculation, a formal issue step, and full lifecycle tracking.",
  },
  {
    icon: Banknote,
    title: "Payments",
    description: "Customer payments recorded and allocated against one or more open invoices.",
  },
  {
    icon: Truck,
    title: "Purchase bills & suppliers",
    description: "A separate vendor master for purchase bills and supplier payments.",
  },
  {
    icon: FileText,
    title: "Reports",
    description: "Business reporting across sales, outstanding balances, and customers.",
  },
  {
    icon: Anchor,
    title: "Documents",
    description: "Business documents — receipts, contracts, and more — attached to the records they belong to.",
  },
];

export function HomePage() {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="border-b">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <FishIcon className="size-4" aria-hidden />
            </div>
            <span className="text-base font-semibold">{SITE_NAME}</span>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto w-full max-w-5xl px-6 py-16 text-center sm:py-24">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{SITE_NAME}</h1>
          <p className="mt-2 text-lg text-muted-foreground">Fishery Management &amp; ERP</p>
          <p className="mx-auto mt-6 max-w-2xl text-balance text-muted-foreground">
            {SITE_NAME} is a business management system for the seafood industry — built for fish
            traders, wholesalers, exporters, and boat owners who are moving off paper records and
            ledger books and onto a single system of record for companies, invoices, payments, and
            trips.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/privacy">Privacy Policy</Link>
            </Button>
          </div>
        </section>

        <section className="border-t bg-muted/30 py-16 sm:py-20">
          <div className="mx-auto w-full max-w-5xl px-6">
            <h2 className="text-center text-2xl font-semibold tracking-tight">What {SITE_NAME} does</h2>
            <p className="mx-auto mt-3 max-w-2xl text-center text-muted-foreground">
              A single record of truth for the trade — replacing handwritten invoices, ledger
              books for company balances, and loose slips for trip expenses.
            </p>

            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {capabilities.map(({ icon: Icon, title, description }) => (
                <Card key={title}>
                  <CardHeader>
                    <Icon className="size-5 text-primary" aria-hidden />
                    <CardTitle className="text-base">{title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 sm:py-20">
          <div className="mx-auto w-full max-w-3xl px-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="size-5 text-primary" aria-hidden />
                  <CardTitle className="text-base">Security &amp; data protection</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Access to {SITE_NAME} requires authentication, and permissions are enforced by
                  role for every user. Passwords are never stored in plain text. The application is
                  served over an encrypted HTTPS connection.
                </p>
                <p>
                  Database backups are taken on a regular schedule and stored off-site, with an
                  encrypted copy kept as the primary backup. See our{" "}
                  <Link href="/privacy" className="text-primary underline underline-offset-4">
                    Privacy Policy
                  </Link>{" "}
                  for more detail on how data is handled.
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}
