import type { Metadata } from "next";

import { HomePage } from "@/features/marketing/pages/home-page";
import { SITE_NAME, SITE_URL } from "@/lib/site-config";

const description =
  "AquaLedger is a fishery management ERP for seafood trading and fishing operations — companies, fish master data, boats, trips, invoices, payments, and reports in one system of record.";

export const metadata: Metadata = {
  title: `${SITE_NAME} — Fishery Management & ERP`,
  description,
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    title: `${SITE_NAME} — Fishery Management & ERP`,
    description,
    url: SITE_URL,
    siteName: SITE_NAME,
    type: "website",
  },
};

export default function Page() {
  return <HomePage />;
}
