"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripCatchForm } from "@/features/trips/components/trip-catch-form";
import { useCreateTripCatch } from "@/features/trips/hooks/use-create-trip-catch";
import {
  toTripCatchRequestPayload,
  type TripCatchFormValues,
} from "@/features/trips/schemas/trip-catch-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * `trip_id` comes from the route (`/trips/{id}/catches/new`), never a form
 * field - `TripCatchForm` has no trip selector, so the user can never
 * associate a catch with the wrong trip (Sprint 6 Session 6's Navigation
 * rule).
 */
export function TripCatchCreatePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const tripId = params.id;
  const { hasPermission } = usePermissions();
  const createTripCatch = useCreateTripCatch();

  if (!hasPermission("trip_catch:create")) {
    return (
      <ErrorState
        title="You don't have permission to record trip catch"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: TripCatchFormValues) {
    const loadingToastId = toastLoading("Recording catch…");
    try {
      await createTripCatch.mutateAsync(toTripCatchRequestPayload(tripId, values));
      dismissToast(loadingToastId);
      toastSuccess("Catch recorded.");
      router.push(`/trips/${tripId}`);
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is TripCatchForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="Add Catch" description="Record a catch landed on this trip.">
      <TripCatchForm
        onSubmit={handleSubmit}
        onCancel={() => router.push(`/trips/${tripId}`)}
        submitLabel="Add Catch"
      />
    </FormPageTemplate>
  );
}
