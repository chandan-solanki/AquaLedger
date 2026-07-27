"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripForm } from "@/features/trips/components/trip-form";
import { useTrip } from "@/features/trips/hooks/use-trip";
import { useUpdateTrip } from "@/features/trips/hooks/use-update-trip";
import {
  toTripFormValues,
  toTripUpdatePayload,
  type TripFormValues,
} from "@/features/trips/schemas/trip-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export function TripEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const tripId = params.id;
  const { hasPermission } = usePermissions();

  const tripQuery = useTrip(tripId);
  const updateTrip = useUpdateTrip();

  if (!hasPermission("trip:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit trips"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = tripQuery.isError ? normalizeApiError(tripQuery.error) : null;

  async function handleSubmit(values: TripFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      const trip = await updateTrip.mutateAsync({
        id: tripId,
        payload: toTripUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess(`${trip.tripNumber} was updated.`);
      router.push("/trips");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is TripForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Trip"
      description={tripQuery.data?.tripNumber}
      isLoading={tripQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load trip record",
              description: apiError.message,
              onRetry: () => tripQuery.refetch(),
            }
          : null
      }
    >
      {tripQuery.data && (
        <TripForm
          defaultValues={toTripFormValues(tripQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/trips")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
