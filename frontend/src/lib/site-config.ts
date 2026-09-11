/**
 * Single source of truth for the public marketing site's identity — used by
 * page metadata (canonical/OG URLs), robots.ts, sitemap.ts, and the
 * homepage/privacy-page copy, so the production URL and support contact
 * only ever need to change in one place.
 */
export const SITE_URL = "https://aqualedger.zenmediahouse.com";
export const SITE_NAME = "AquaLedger";

/**
 * No real public support/contact address exists anywhere in this repo yet
 * (only the seeded internal dev account, admin@fisherp.local, which is not
 * a public contact). Replace with a real monitored address before relying
 * on this for the Google OAuth consent screen or the privacy policy.
 */
export const SUPPORT_EMAIL_PLACEHOLDER = "[SUPPORT_EMAIL_NOT_YET_CONFIGURED]";
