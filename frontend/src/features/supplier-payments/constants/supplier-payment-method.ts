import type { StatusFilterOption } from "@/components/filters";
import type { SupplierPaymentMethod } from "@/features/supplier-payments/types/supplier-payment";

export const SUPPLIER_PAYMENT_METHOD_VALUES = [
  "cash",
  "upi",
  "cheque",
  "bank_transfer",
  "card",
  "adjustment",
] as const satisfies readonly SupplierPaymentMethod[];

export const SUPPLIER_PAYMENT_METHOD_OPTIONS: StatusFilterOption<SupplierPaymentMethod>[] = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "cheque", label: "Cheque" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "card", label: "Card" },
  { value: "adjustment", label: "Adjustment" },
];

export const SUPPLIER_PAYMENT_METHOD_LABELS: Record<SupplierPaymentMethod, string> = {
  cash: "Cash",
  upi: "UPI",
  cheque: "Cheque",
  bank_transfer: "Bank Transfer",
  card: "Card",
  adjustment: "Adjustment",
};
