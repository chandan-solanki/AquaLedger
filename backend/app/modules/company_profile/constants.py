"""Logo upload limits for the Company Profile module (Sprint 14). Kept as
plain module constants (not a DB-backed setting) since these are
validation rules, not tenant-configurable behaviour - mirrors how
password_min_length etc. live as constants in app.core.config rather
than per-tenant data.
"""

MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB - a header logo never needs more.

# Deliberately narrow: a company logo is a print/display asset, never an
# arbitrary upload - SVG/GIF/BMP and any executable/document type are
# rejected outright rather than allow-listed by exclusion.
ALLOWED_LOGO_CONTENT_TYPES: frozenset[str] = frozenset({"image/png", "image/jpeg", "image/webp"})

# One extension per allowed content-type, used to build the storage key -
# the client-supplied filename's own extension is never trusted.
LOGO_EXTENSION_BY_CONTENT_TYPE: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
