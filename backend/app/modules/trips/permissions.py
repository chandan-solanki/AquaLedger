# Permission codes for the trips module, per ARCHITECTURE.md §9.2.
# trip:view/create/edit/close were seeded in migration 67c33121fc54
# (auth_and_tenancy_tables) alongside the rest of the initial permission set.
# trip:delete was added in 244f758929a6 for the Session 2 DELETE endpoint.
TRIP_VIEW = "trip:view"
TRIP_CREATE = "trip:create"
TRIP_EDIT = "trip:edit"
TRIP_CLOSE = "trip:close"
TRIP_DELETE = "trip:delete"
