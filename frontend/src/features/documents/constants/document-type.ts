import type { StatusFilterOption } from "@/components/filters";
import type { DocumentPartyType, DocumentType } from "@/features/documents/types/document";

/**
 * A label for every `DocumentType` the backend's enum defines — including
 * `purchase_order`/`delivery_challan`, so a record's `document_type` never
 * falls back to its raw enum value just because no renderer emits that type
 * yet (see `types/document.ts`).
 */
export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  invoice: "Invoice",
  purchase_bill: "Purchase Bill",
  customer_payment_receipt: "Customer Payment Receipt",
  supplier_payment_receipt: "Supplier Payment Receipt",
  purchase_order: "Purchase Order",
  delivery_challan: "Delivery Challan",
};

/**
 * Only the four document types with a renderer actually registered
 * (a prior session's domain audit deliberately did not build Purchase
 * Order/Delivery Challan yet) — the only ones offered as a filter choice,
 * since selecting either of the other two enum values could only ever
 * return zero results.
 */
export const DOCUMENT_TYPE_FILTER_VALUES = [
  "invoice",
  "purchase_bill",
  "customer_payment_receipt",
  "supplier_payment_receipt",
] as const satisfies readonly DocumentType[];

export type DocumentTypeFilter = (typeof DOCUMENT_TYPE_FILTER_VALUES)[number];

export const DOCUMENT_TYPE_OPTIONS: StatusFilterOption<DocumentTypeFilter>[] = DOCUMENT_TYPE_FILTER_VALUES.map(
  (value) => ({ value, label: DOCUMENT_TYPE_LABELS[value] })
);

export const DOCUMENT_PARTY_TYPE_VALUES = [
  "customer",
  "supplier",
] as const satisfies readonly DocumentPartyType[];

export const DOCUMENT_PARTY_TYPE_LABELS: Record<DocumentPartyType, string> = {
  customer: "Customer",
  supplier: "Supplier",
};

export const DOCUMENT_PARTY_TYPE_OPTIONS: StatusFilterOption<DocumentPartyType>[] =
  DOCUMENT_PARTY_TYPE_VALUES.map((value) => ({ value, label: DOCUMENT_PARTY_TYPE_LABELS[value] }));
