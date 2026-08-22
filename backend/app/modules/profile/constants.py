"""Avatar upload limits for the self-service Profile module (Sprint 16).

Deliberately a separate set of constants from
app.modules.company_profile.constants rather than a shared import - a
user's avatar and a tenant's logo are different resources that happen to
share the same limits today, the same reasoning auth/schemas.py and
users/schemas.py each keep their own copy of the email regex instead of
sharing one.
"""

MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB - an avatar never needs more.

# Deliberately narrow: an avatar is a display asset, never an arbitrary
# upload - SVG/GIF/BMP and any executable/document type are rejected
# outright rather than allow-listed by exclusion.
ALLOWED_AVATAR_CONTENT_TYPES: frozenset[str] = frozenset({"image/png", "image/jpeg", "image/webp"})

# One extension per allowed content-type, used to build the storage key -
# the client-supplied filename's own extension is never trusted.
AVATAR_EXTENSION_BY_CONTENT_TYPE: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
