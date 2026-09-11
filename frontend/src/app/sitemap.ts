import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

/**
 * Only the two genuinely public routes — every authenticated app route is
 * deliberately excluded (see robots.ts and middleware.ts).
 */
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: SITE_URL, changeFrequency: "monthly", priority: 1 },
    { url: `${SITE_URL}/privacy`, changeFrequency: "yearly", priority: 0.3 },
  ];
}
