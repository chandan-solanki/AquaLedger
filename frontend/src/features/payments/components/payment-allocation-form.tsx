"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { AsyncSelect, CurrencyInput, FormActions, FormGrid } from "@/components/form";
import type { ComboboxOption } from "@/components/form";
import { Button } from "@/components/ui/button";
import { INVOICE_STATUS_LABELS, invoiceKeys, invoiceService } from "@/features/invoices";
import type { Invoice, InvoiceStatus } from "@/features/invoices";
import { useSearch } from "@/hooks/use-search";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatCurrency } from "@/utils/format-currency";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

// allocated_amount: Decimal, max_digits=14, decimal_places=2, gt=0 (app/modules/payments/schemas.py).
const AMOUNT_PATTERN = /^\d{1,12}(\.\d{1,2})?$/;

const amountField = z
  .string()
  .trim()
  .min(1, "Allocation amount is required")
  .refine((value) => AMOUNT_PATTERN.test(value), "Enter a valid amount (up to 2 decimal places)")
  .refine((value) => Number(value) > 0, "Must be greater than 0");

/**
 * Fields match PaymentAllocationCreateRequest/PaymentAllocationUpdateRequest
 * exactly (app/modules/payments/schemas.py) - just the two the backend
 * accepts, nothing else. Colocated here rather than a separate schemas/ file
 * since the form itself is this small (unlike the header forms' larger
 * field sets).
 */
const paymentAllocationFormSchema = z.object({
  invoice_id: z.string().trim().min(1, "Invoice is required"),
  allocated_amount: amountField,
});

export type PaymentAllocationFormValues = z.infer<typeof paymentAllocationFormSchema>;

export const DEFAULT_PAYMENT_ALLOCATION_FORM_VALUES: PaymentAllocationFormValues = {
  invoice_id: "",
  allocated_amount: "",
};

export interface PaymentAllocationFormProps {
  /** The owning payment's `company_id` - scopes the Invoice search to that company's own invoices (a real, backend-supported `company_id` filter), a UX convenience only: the backend itself never requires an allocation's invoice to belong to the same company as the payment. */
  companyId: string;
  /** The owning payment's current `unallocated_amount` - shown as an informational hint only, never enforced client-side (see this component's own docstring). */
  paymentUnallocatedAmount: string;
  /** Present for Edit (populated from the loaded allocation record); omitted for Create (empty form). */
  defaultValues?: PaymentAllocationFormValues;
  onSubmit: (values: PaymentAllocationFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

const ALLOCATABLE_INVOICE_STATUSES: InvoiceStatus[] = ["issued", "partially_paid"];

interface InvoiceSelectorFieldProps {
  value: string;
  companyId: string;
  error?: string;
  onSelect: (invoice: Invoice) => void;
}

/**
 * A searchable Invoice selector, reusing the Invoices feature's own public
 * `invoiceService`/`invoiceKeys` (`@/features/invoices`) - no lookup logic
 * duplicated here, mirroring `TripCatchSelectorField`
 * (`invoice-item-form.tsx`). Typeahead is driven by the backend's own
 * `GET /invoices` search (`q` matches invoice_number and the billed
 * company's name), scoped to the owning payment's company via the real
 * `company_id` filter. Results are narrowed to `issued`/`partially_paid`
 * invoices client-side - a plain filter on an already-fetched `status`
 * field, not a computation - since those are the only statuses the backend
 * accepts for a new allocation (app/modules/payments/service.py's
 * `_ALLOCATABLE_INVOICE_STATUSES`); the backend remains the actual
 * authority (422 `PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS` otherwise).
 * Each option's description shows status and current balance so the user
 * can judge fit without leaving the form. The currently selected invoice is
 * always resolved by id and merged into `options`, so Edit mode shows a
 * correct label immediately, before the user has typed anything.
 */
function InvoiceSelectorField({ value, companyId, error, onSelect }: InvoiceSelectorFieldProps) {
  const search = useSearch({ debounceMs: 300 });

  const searchQuery = useQuery({
    queryKey: ["invoices", "search", companyId, search.debouncedValue],
    queryFn: () =>
      invoiceService.listInvoices({
        q: search.debouncedValue || undefined,
        company_id: companyId,
        sort: "-invoice_date",
        page: 1,
        page_size: 20,
      }),
  });

  const selectedInvoiceQuery = useQuery({
    queryKey: invoiceKeys.detail(value),
    queryFn: () => invoiceService.getInvoice(value),
    enabled: Boolean(value),
    staleTime: 5 * 60 * 1000,
  });

  const invoices = useMemo(() => {
    const results = (searchQuery.data?.data ?? []).filter((invoice) =>
      ALLOCATABLE_INVOICE_STATUSES.includes(invoice.status)
    );
    if (selectedInvoiceQuery.data && !results.some((invoice) => invoice.id === selectedInvoiceQuery.data!.id)) {
      return [selectedInvoiceQuery.data, ...results];
    }
    return results;
  }, [searchQuery.data, selectedInvoiceQuery.data]);

  const options = useMemo<ComboboxOption[]>(
    () =>
      invoices.map((invoice) => ({
        value: invoice.id,
        label: invoice.invoiceNumber ?? "Draft invoice",
        description: `${INVOICE_STATUS_LABELS[invoice.status]} · Balance: ${formatCurrency(invoice.balanceAmount)}`,
      })),
    [invoices]
  );

  const selectedOption = options.find((option) => option.value === value);

  return (
    <div className="space-y-1.5 md:col-span-full">
      <AsyncSelect
        label="Invoice"
        required
        placeholder="Search by invoice number…"
        searchPlaceholder="Search invoices…"
        options={options}
        value={value || undefined}
        onSearchChange={search.setValue}
        isLoading={searchQuery.isFetching || selectedInvoiceQuery.isLoading}
        onChange={(selectedId) => {
          const chosen = invoices.find((invoice) => invoice.id === selectedId);
          if (chosen) onSelect(chosen);
        }}
        error={error}
      />
      {selectedOption?.description && (
        <p className="px-1 text-xs text-muted-foreground">{selectedOption.description}</p>
      )}
    </div>
  );
}

/**
 * The shared Payment Allocation Create/Edit form - just the two fields the
 * backend accepts (Invoice, Allocation Amount), rendered inside a Dialog on
 * the Payment Detail page (`PaymentAllocationTable`), not a routed page.
 *
 * The backend's two allocation ceilings - `allocated_amount` must not
 * exceed the invoice's current `balance_amount` nor the payment's current
 * `unallocated_amount` (app/modules/payments/domain/allocation.py's
 * `validate_allocation_amount`) - are deliberately left server-validated
 * only, surfacing as the generic 422 toast below: for an update, the
 * backend adjusts both ceilings by adding back this same allocation's own
 * prior amount before comparing, a live, transaction-scoped calculation
 * this form has no way to reproduce safely from cached data without risking
 * drift from the source of truth. This mirrors how `InvoiceItemForm`/
 * `TripCatchSelectorField` leave their own cross-entity ceiling ("quantity
 * exceeds available_quantity") server-validated only. Both ceiling values
 * are still shown as informational hints - the invoice's balance in the
 * Invoice selector's option description, the payment's unallocated amount
 * under Allocation Amount - so the user rarely needs the round trip to find
 * out.
 */
export function PaymentAllocationForm({
  companyId,
  paymentUnallocatedAmount,
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: PaymentAllocationFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<PaymentAllocationFormValues>({
    resolver: zodResolver(paymentAllocationFormSchema),
    defaultValues: defaultValues ?? DEFAULT_PAYMENT_ALLOCATION_FORM_VALUES,
  });

  async function handleFormSubmit(values: PaymentAllocationFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<PaymentAllocationFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormGrid columns={2}>
        <InvoiceSelectorField
          value={watch("invoice_id")}
          companyId={companyId}
          error={errors.invoice_id?.message}
          onSelect={(invoice) => setValue("invoice_id", invoice.id, { shouldValidate: true })}
        />

        <CurrencyInput
          label="Allocation Amount"
          required
          description={`Up to ${formatCurrency(paymentUnallocatedAmount)} unallocated on this payment.`}
          error={errors.allocated_amount?.message}
          {...register("allocated_amount")}
        />
      </FormGrid>

      <FormActions
        secondary={
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        }
        primary={
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
            {isSubmitting ? "Saving…" : submitLabel}
          </Button>
        }
      />
    </form>
  );
}
