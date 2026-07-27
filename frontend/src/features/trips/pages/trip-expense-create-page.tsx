"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripExpenseForm } from "@/features/trips/components/trip-expense-form";
import { useCreateTripExpense } from "@/features/trips/hooks/use-create-trip-expense";
import {
  toTripExpenseRequestPayload,
  type TripExpenseFormValues,
} from "@/features/trips/schemas/trip-expense-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * `trip_id` comes from the route (`/trips/{id}/expenses/new`), never a form
 * field - `TripExpenseForm` has no trip selector, so the user can never
 * associate an expense with the wrong trip (Sprint 6 Session 6's
 * Navigation rule).
 */
export function TripExpenseCreatePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const tripId = params.id;
  const { hasPermission } = usePermissions();
  const createTripExpense = useCreateTripExpense();

  if (!hasPermission("trip_expense:create")) {
    return (
      <ErrorState
        title="You don't have permission to record trip expenses"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: TripExpenseFormValues) {
    const loadingToastId = toastLoading("Recording expense…");
    try {
      await createTripExpense.mutateAsync(toTripExpenseRequestPayload(tripId, values));
      dismissToast(loadingToastId);
      toastSuccess("Expense recorded.");
      router.push(`/trips/${tripId}`);
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is TripExpenseForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="Add Expense" description="Record an expense incurred on this trip.">
      <TripExpenseForm
        onSubmit={handleSubmit}
        onCancel={() => router.push(`/trips/${tripId}`)}
        submitLabel="Add Expense"
      />
    </FormPageTemplate>
  );
}
