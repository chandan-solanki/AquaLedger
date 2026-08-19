export type NumberingDocumentType =
  | "invoice"
  | "purchase_bill"
  | "purchase_order"
  | "customer_payment"
  | "supplier_payment"
  | "delivery_challan";

export type NumberingSequenceStatus = "active" | "not_started";

/** Raw backend shape, matching NumberingSequenceResponse (backend/app/modules/numbering_sequences/schemas.py) exactly. */
export interface BackendNumberingSequence {
  document_type: NumberingDocumentType;
  document_label: string;
  prefix: string;
  fiscal_year: string;
  current_number: number;
  next_number: number;
  next_number_formatted: string;
  number_format: string;
  status: NumberingSequenceStatus;
}

/** The client-facing, camelCase shape every numbering-sequence-service.ts function returns. */
export interface NumberingSequence {
  documentType: NumberingDocumentType;
  documentLabel: string;
  prefix: string;
  fiscalYear: string;
  currentNumber: number;
  nextNumber: number;
  nextNumberFormatted: string;
  numberFormat: string;
  status: NumberingSequenceStatus;
}

export function mapBackendNumberingSequence(
  sequence: BackendNumberingSequence
): NumberingSequence {
  return {
    documentType: sequence.document_type,
    documentLabel: sequence.document_label,
    prefix: sequence.prefix,
    fiscalYear: sequence.fiscal_year,
    currentNumber: sequence.current_number,
    nextNumber: sequence.next_number,
    nextNumberFormatted: sequence.next_number_formatted,
    numberFormat: sequence.number_format,
    status: sequence.status,
  };
}
