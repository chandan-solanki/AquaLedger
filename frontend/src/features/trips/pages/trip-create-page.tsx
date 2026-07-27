"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripForm } from "@/features/trips/components/trip-form";
import { useCreateTrip } from "@/features/trips/hooks/use-create-trip";
import { toTripRequestPayload, type TripFormValues } from "@/features/trips/schemas/trip-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

export function TripCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createTrip = useCreateTrip();

  if (!hasPermission("trip:create")) {
    return (
      <ErrorState
        title="You don't have permission to create trips"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: TripFormValues) {
    const loadingToastId = toastLoading("Creating trip…");
    try {
      const trip = await createTrip.mutateAsync(toTripRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess(`${trip.tripNumber} was created.`);
      router.push("/trips");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is TripForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Trip" description="Log a trip for one of your boats.">
      <TripForm onSubmit={handleSubmit} onCancel={() => router.push("/trips")} submitLabel="Create Trip" />
    </FormPageTemplate>
  );
}
