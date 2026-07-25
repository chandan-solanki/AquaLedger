import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import type { ApiFieldErrors } from "@/types/api";

/**
 * Maps backend 422 field errors onto React Hook Form fields, so a
 * server-side validation error renders identically to a client-side one
 * (07_FRONTEND_ARCHITECTURE.md §12, 04_USER_FLOWS.md §4).
 */
export function mapServerErrorsToForm<T extends FieldValues>(
  fieldErrors: ApiFieldErrors,
  setError: UseFormSetError<T>
): void {
  for (const [field, messages] of Object.entries(fieldErrors)) {
    setError(field as Path<T>, { type: "server", message: messages.join(" ") });
  }
}
