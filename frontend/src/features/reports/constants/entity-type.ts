/** Mirrors the backend's EntityType enum (app/modules/reports/constants.py) - the Outstanding/Aging Report's tab selector. */
export type EntityType = "customer" | "supplier";

export const ENTITY_TYPE_VALUES = ["customer", "supplier"] as const satisfies readonly EntityType[];
