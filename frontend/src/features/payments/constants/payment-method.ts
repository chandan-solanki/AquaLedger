import type { StatusFilterOption } from "@/components/filters";
import type { PaymentMethod } from "@/features/payments/types/payment";

export const PAYMENT_METHOD_VALUES = [
  "cash",
  "upi",
  "cheque",
  "bank_transfer",
  "card",
  "adjustment",
] as const satisfies readonly PaymentMethod[];

export const PAYMENT_METHOD_OPTIONS: StatusFilterOption<PaymentMethod>[] = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "cheque", label: "Cheque" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "card", label: "Card" },
  { value: "adjustment", label: "Adjustment" },
];

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: "Cash",
  upi: "UPI",
  cheque: "Cheque",
  bank_transfer: "Bank Transfer",
  card: "Card",
  adjustment: "Adjustment",
};
