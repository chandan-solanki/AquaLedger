/** No params — the dashboard endpoint takes none (it's always "my tenant, right now"), so `summary()` is a fixed key, unlike `boatKeys.list(params)`. */
export const dashboardKeys = {
  all: () => ["dashboard"] as const,
  summary: () => [...dashboardKeys.all(), "summary"] as const,
};
