import type { DocumentPartyType, SourceType } from "@/features/documents/types/document";

/**
 * Where "Document Number" navigates for each `source_type`, and the
 * permission required to follow that link (Sprint 12 Session 8). Kept as a
 * closed, centralized mapping rather than building a route from
 * `source_type` directly — a source route/permission must never be
 * constructed from an arbitrary string, even one that came from our own
 * backend response (a schema drift or a future unmapped source_type must
 * degrade to "no navigation", never a broken or unsafe route).
 */
export const SOURCE_TYPE_ROUTES: Record<SourceType, string> = {
  invoice: "/invoices",
  purchase_bill: "/purchase-bills",
  payment: "/payments",
  supplier_payment: "/supplier-payments",
};

export const SOURCE_TYPE_PERMISSIONS: Record<SourceType, string> = {
  invoice: "invoice:view",
  purchase_bill: "purchase:view",
  payment: "payment:view",
  supplier_payment: "supplier_payment:view",
};

const KNOWN_SOURCE_TYPES: readonly SourceType[] = [
  "invoice",
  "purchase_bill",
  "payment",
  "supplier_payment",
];

function isKnownSourceType(value: string): value is SourceType {
  return (KNOWN_SOURCE_TYPES as readonly string[]).includes(value);
}

/**
 * Resolves the source-document detail route, or `null` if there is
 * nothing to navigate to - either field is missing (Sessions 6/7 records
 * have neither), or `sourceType` isn't one of the known, mapped values.
 * Permission gating happens separately at the call site via
 * `SOURCE_TYPE_PERMISSIONS`, not here.
 */
export function getSourceHref(sourceType: string | null, sourceId: string | null): string | null {
  if (!sourceType || !sourceId || !isKnownSourceType(sourceType)) return null;
  return `${SOURCE_TYPE_ROUTES[sourceType]}/${sourceId}`;
}

/** Where the Party column navigates: Customer -> Company detail, Supplier -> Supplier detail. */
export const PARTY_TYPE_ROUTES: Record<DocumentPartyType, string> = {
  customer: "/companies",
  supplier: "/suppliers",
};

export const PARTY_TYPE_PERMISSIONS: Record<DocumentPartyType, string> = {
  customer: "company:view",
  supplier: "supplier:view",
};

export function getPartyHref(
  partyType: DocumentPartyType | null,
  partyId: string | null
): string | null {
  if (!partyType || !partyId) return null;
  return `${PARTY_TYPE_ROUTES[partyType]}/${partyId}`;
}
