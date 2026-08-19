# Reuses the "user:manage" permission seeded by the baseline auth migration
# (67c33121fc54) rather than introducing user:view/user:create/user:edit -
# it already gates the Administration -> Users nav entry (frontend
# navigation.ts) and is granted only to super_admin/admin in the seed data.
USER_MANAGE_PERMISSION = "user:manage"
