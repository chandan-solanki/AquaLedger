import type { Metadata } from "next";

import { PrivacyPage } from "@/features/marketing/pages/privacy-page";
import { SITE_NAME, SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: `Privacy Policy — ${SITE_NAME}`,
  description: `How ${SITE_NAME} collects, stores, and protects data for the businesses and users that operate it.`,
  alternates: {
    canonical: `${SITE_URL}/privacy`,
  },
  openGraph: {
    title: `Privacy Policy — ${SITE_NAME}`,
    url: `${SITE_URL}/privacy`,
    siteName: SITE_NAME,
    type: "website",
  },
};

export default function Page() {
  return <PrivacyPage />;
}
