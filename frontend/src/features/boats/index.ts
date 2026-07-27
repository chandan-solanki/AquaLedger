export { BoatListPage } from "@/features/boats/pages/boat-list-page";
export { BoatCreatePage } from "@/features/boats/pages/boat-create-page";
export { BoatEditPage } from "@/features/boats/pages/boat-edit-page";
export { BoatDetailPage } from "@/features/boats/pages/boat-detail-page";

export { BoatForm, type BoatFormProps } from "@/features/boats/components/boat-form";

export { useBoats } from "@/features/boats/hooks/use-boats";
export { useBoatFilters } from "@/features/boats/hooks/use-boat-filters";
export { useBoat } from "@/features/boats/hooks/use-boat";
export { useCreateBoat } from "@/features/boats/hooks/use-create-boat";
export { useUpdateBoat, type UpdateBoatVariables } from "@/features/boats/hooks/use-update-boat";
export { useDeleteBoat } from "@/features/boats/hooks/use-delete-boat";

export { boatService } from "@/features/boats/services/boat-service";
export type { BoatListResult } from "@/features/boats/services/boat-service";

export type {
  BackendBoat,
  Boat,
  BoatCreateRequest,
  BoatListParams,
  BoatUpdateRequest,
} from "@/features/boats/types/boat";
export { mapBackendBoat } from "@/features/boats/types/boat";

export type { BoatFilters, BoatSortDirection, BoatSortField } from "@/features/boats/schemas/boat-filters";
export {
  BOAT_SORT_DIRECTIONS,
  BOAT_SORT_FIELDS,
  DEFAULT_BOAT_FILTERS,
  toBoatListParams,
} from "@/features/boats/schemas/boat-filters";

export type { BoatFormValues } from "@/features/boats/schemas/boat-form-schema";
export {
  DEFAULT_BOAT_FORM_VALUES,
  boatFormSchema,
  toBoatFormValues,
  toBoatRequestPayload,
  toBoatUpdatePayload,
} from "@/features/boats/schemas/boat-form-schema";

export type { BoatStatus } from "@/features/boats/constants/boat-status";
export {
  BOAT_STATUS_BADGE_VARIANT,
  BOAT_STATUS_LABELS,
  BOAT_STATUS_OPTIONS,
  BOAT_STATUS_VALUES,
  toBoatStatus,
} from "@/features/boats/constants/boat-status";

export { boatKeys } from "@/features/boats/constants/query-keys";
