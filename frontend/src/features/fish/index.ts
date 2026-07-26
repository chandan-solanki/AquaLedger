export { FishListPage } from "@/features/fish/pages/fish-list-page";
export { FishCreatePage } from "@/features/fish/pages/fish-create-page";
export { FishEditPage } from "@/features/fish/pages/fish-edit-page";
export { FishDetailPage } from "@/features/fish/pages/fish-detail-page";

export { FishForm, type FishFormProps } from "@/features/fish/components/fish-form";

export { useFishes } from "@/features/fish/hooks/use-fishes";
export { useFishFilters } from "@/features/fish/hooks/use-fish-filters";
export { useFish } from "@/features/fish/hooks/use-fish";
export { useCreateFish } from "@/features/fish/hooks/use-create-fish";
export { useUpdateFish, type UpdateFishVariables } from "@/features/fish/hooks/use-update-fish";
export { useDeleteFish } from "@/features/fish/hooks/use-delete-fish";

export { fishService } from "@/features/fish/services/fish-service";
export type { FishListResult } from "@/features/fish/services/fish-service";

export type {
  BackendFish,
  Fish,
  FishCreateRequest,
  FishListParams,
  FishUnit,
  FishUpdateRequest,
} from "@/features/fish/types/fish";
export {
  FISH_UNIT_LABELS,
  FISH_UNIT_OPTIONS,
  FISH_UNIT_VALUES,
  mapBackendFish,
} from "@/features/fish/types/fish";

export type { FishFilters, FishSortDirection, FishSortField } from "@/features/fish/schemas/fish-filters";
export {
  DEFAULT_FISH_FILTERS,
  FISH_SORT_DIRECTIONS,
  FISH_SORT_FIELDS,
  toFishListParams,
} from "@/features/fish/schemas/fish-filters";

export type { FishFormValues } from "@/features/fish/schemas/fish-form-schema";
export {
  DEFAULT_FISH_FORM_VALUES,
  fishFormSchema,
  toFishFormValues,
  toFishRequestPayload,
  toFishUpdatePayload,
} from "@/features/fish/schemas/fish-form-schema";

export type { FishStatus } from "@/features/fish/constants/fish-status";
export {
  FISH_STATUS_BADGE_VARIANT,
  FISH_STATUS_LABELS,
  FISH_STATUS_OPTIONS,
  FISH_STATUS_VALUES,
  toFishStatus,
} from "@/features/fish/constants/fish-status";

export { fishKeys } from "@/features/fish/constants/query-keys";
