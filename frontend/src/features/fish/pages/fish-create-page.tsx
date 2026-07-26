"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { FishForm } from "@/features/fish/components/fish-form";
import { useCreateFish } from "@/features/fish/hooks/use-create-fish";
import { toFishRequestPayload, type FishFormValues } from "@/features/fish/schemas/fish-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

export function FishCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createFish = useCreateFish();

  if (!hasPermission("fish:manage")) {
    return (
      <ErrorState
        title="You don't have permission to create fish records"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: FishFormValues) {
    const loadingToastId = toastLoading("Creating fish record…");
    try {
      const fish = await createFish.mutateAsync(toFishRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess(`${fish.name} was created.`);
      router.push("/fish");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is FishForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Fish" description="Add a fish master record.">
      <FishForm onSubmit={handleSubmit} onCancel={() => router.push("/fish")} submitLabel="Create Fish" />
    </FormPageTemplate>
  );
}
