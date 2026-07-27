"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripCatchForm } from "@/features/trips/components/trip-catch-form";
import { useTripCatch } from "@/features/trips/hooks/use-trip-catch";
import { useUpdateTripCatch } from "@/features/trips/hooks/use-update-trip-catch";
import {
  toTripCatchFormValues,
  toTripCatchUpdatePayload,
  type TripCatchFormValues,
} from "@/features/trips/schemas/trip-catch-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Serves both "Edit" and "View" (`useTripCatchRowActions`'s single combined
 * row action) - gated on `trip_catch:view` to load the record at all, then
 * renders `TripCatchForm` in its `readOnly` mode when the caller lacks
 * `trip_catch:edit`, per this session's Trip Detail page's row-action
 * design (there is no separate Trip Catch detail page).
 */
export function TripCatchEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string; catchId: string }>();
  const tripId = params.id;
  const catchId = params.catchId;
  const { hasPermission } = usePermissions();

  const tripCatchQuery = useTripCatch(catchId);
  const updateTripCatch = useUpdateTripCatch();

  if (!hasPermission("trip_catch:view")) {
    return (
      <ErrorState
        title="You don't have permission to view trip catch records"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = tripCatchQuery.isError ? normalizeApiError(tripCatchQuery.error) : null;
  const canEdit = hasPermission("trip_catch:edit");

  async function handleSubmit(values: TripCatchFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updateTripCatch.mutateAsync({ id: catchId, payload: toTripCatchUpdatePayload(values) });
      dismissToast(loadingToastId);
      toastSuccess("Catch record updated.");
      router.push(`/trips/${tripId}`);
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is TripCatchForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title={canEdit ? "Edit Catch" : "View Catch"}
      isLoading={tripCatchQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load trip catch record",
              description: apiError.message,
              onRetry: () => tripCatchQuery.refetch(),
            }
          : null
      }
    >
      {tripCatchQuery.data && (
        <TripCatchForm
          defaultValues={toTripCatchFormValues(tripCatchQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push(`/trips/${tripId}`)}
          submitLabel="Save Changes"
          readOnly={!canEdit}
        />
      )}
    </FormPageTemplate>
  );
}
