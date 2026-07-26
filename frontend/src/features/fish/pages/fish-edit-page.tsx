"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { FishForm } from "@/features/fish/components/fish-form";
import { useFish } from "@/features/fish/hooks/use-fish";
import { useUpdateFish } from "@/features/fish/hooks/use-update-fish";
import {
  toFishFormValues,
  toFishUpdatePayload,
  type FishFormValues,
} from "@/features/fish/schemas/fish-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export function FishEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const fishId = params.id;
  const { hasPermission } = usePermissions();

  const fishQuery = useFish(fishId);
  const updateFish = useUpdateFish();

  if (!hasPermission("fish:manage")) {
    return (
      <ErrorState
        title="You don't have permission to edit fish records"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = fishQuery.isError ? normalizeApiError(fishQuery.error) : null;

  async function handleSubmit(values: FishFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      const fish = await updateFish.mutateAsync({
        id: fishId,
        payload: toFishUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess(`${fish.name} was updated.`);
      router.push("/fish");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is FishForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Fish"
      description={fishQuery.data?.name}
      isLoading={fishQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load fish record",
              description: apiError.message,
              onRetry: () => fishQuery.refetch(),
            }
          : null
      }
    >
      {fishQuery.data && (
        <FishForm
          defaultValues={toFishFormValues(fishQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/fish")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
