"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripExpenseForm } from "@/features/trips/components/trip-expense-form";
import { useTripExpense } from "@/features/trips/hooks/use-trip-expense";
import { useUpdateTripExpense } from "@/features/trips/hooks/use-update-trip-expense";
import {
  toTripExpenseFormValues,
  toTripExpenseUpdatePayload,
  type TripExpenseFormValues,
} from "@/features/trips/schemas/trip-expense-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Serves both "Edit" and "View" (`useTripExpenseRowActions`'s single
 * combined row action) - gated on `trip_expense:view` to load the record at
 * all, then renders `TripExpenseForm` in its `readOnly` mode when the
 * caller lacks `trip_expense:edit`, per this session's Trip Detail page's
 * row-action design (there is no separate Trip Expense detail page).
 */
export function TripExpenseEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string; expenseId: string }>();
  const tripId = params.id;
  const expenseId = params.expenseId;
  const { hasPermission } = usePermissions();

  const tripExpenseQuery = useTripExpense(expenseId);
  const updateTripExpense = useUpdateTripExpense();

  if (!hasPermission("trip_expense:view")) {
    return (
      <ErrorState
        title="You don't have permission to view trip expense records"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = tripExpenseQuery.isError ? normalizeApiError(tripExpenseQuery.error) : null;
  const canEdit = hasPermission("trip_expense:edit");

  async function handleSubmit(values: TripExpenseFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updateTripExpense.mutateAsync({
        id: expenseId,
        payload: toTripExpenseUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess("Expense record updated.");
      router.push(`/trips/${tripId}`);
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is TripExpenseForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title={canEdit ? "Edit Expense" : "View Expense"}
      isLoading={tripExpenseQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load trip expense record",
              description: apiError.message,
              onRetry: () => tripExpenseQuery.refetch(),
            }
          : null
      }
    >
      {tripExpenseQuery.data && (
        <TripExpenseForm
          defaultValues={toTripExpenseFormValues(tripExpenseQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push(`/trips/${tripId}`)}
          submitLabel="Save Changes"
          readOnly={!canEdit}
        />
      )}
    </FormPageTemplate>
  );
}
