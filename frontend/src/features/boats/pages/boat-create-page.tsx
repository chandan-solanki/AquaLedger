"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { BoatForm } from "@/features/boats/components/boat-form";
import { useCreateBoat } from "@/features/boats/hooks/use-create-boat";
import { toBoatRequestPayload, type BoatFormValues } from "@/features/boats/schemas/boat-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

export function BoatCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createBoat = useCreateBoat();

  if (!hasPermission("boat:create")) {
    return (
      <ErrorState
        title="You don't have permission to create boats"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: BoatFormValues) {
    const loadingToastId = toastLoading("Creating boat…");
    try {
      const boat = await createBoat.mutateAsync(toBoatRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess(`${boat.name} was created.`);
      router.push("/boats");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is BoatForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Boat" description="Add a boat record.">
      <BoatForm onSubmit={handleSubmit} onCancel={() => router.push("/boats")} submitLabel="Create Boat" />
    </FormPageTemplate>
  );
}
