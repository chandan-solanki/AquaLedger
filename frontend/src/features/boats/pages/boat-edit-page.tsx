"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { BoatForm } from "@/features/boats/components/boat-form";
import { useBoat } from "@/features/boats/hooks/use-boat";
import { useUpdateBoat } from "@/features/boats/hooks/use-update-boat";
import {
  toBoatFormValues,
  toBoatUpdatePayload,
  type BoatFormValues,
} from "@/features/boats/schemas/boat-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export function BoatEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const boatId = params.id;
  const { hasPermission } = usePermissions();

  const boatQuery = useBoat(boatId);
  const updateBoat = useUpdateBoat();

  if (!hasPermission("boat:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit boats"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = boatQuery.isError ? normalizeApiError(boatQuery.error) : null;

  async function handleSubmit(values: BoatFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      const boat = await updateBoat.mutateAsync({
        id: boatId,
        payload: toBoatUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess(`${boat.name} was updated.`);
      router.push("/boats");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is BoatForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Boat"
      description={boatQuery.data?.name}
      isLoading={boatQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load boat record",
              description: apiError.message,
              onRetry: () => boatQuery.refetch(),
            }
          : null
      }
    >
      {boatQuery.data && (
        <BoatForm
          defaultValues={toBoatFormValues(boatQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/boats")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
