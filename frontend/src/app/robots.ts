import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

/**
 * Only the public marketing homepage and privacy policy are indexable —
 * every other route requires authentication and must never be crawled.
 * "Allow: /$" + "Disallow: /" is the standard pattern for "index nothing
 * except these exact/prefixed paths" (Google's robots parser resolves the
 * longer/more specific Allow over the blanket Disallow).
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/$", "/privacy"],
        disallow: "/",
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
