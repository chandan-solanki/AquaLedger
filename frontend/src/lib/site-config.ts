/**
 * Single source of truth for the public marketing site's identity — used by
 * page metadata (canonical/OG URLs), robots.ts, sitemap.ts, and the
 * homepage/privacy-page copy, so the production URL and support contact
 * only ever need to change in one place.
 */
export const SITE_URL = "https://aqualedger.zenmediahouse.com";
export const SITE_NAME = "AquaLedger";

/**
 * The support/contact address shown on the public homepage, footer, and
 * privacy policy — kept here as the single source so it's never
 * hardcoded in more than one place.
 */
export const SUPPORT_EMAIL = "chandansolanki618@gmail.com";
