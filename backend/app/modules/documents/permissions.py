# Permission code for the Document Center (Sprint 12 Session 6), per
# ARCHITECTURE.md §9.2's resource:action convention. The Document Center is
# read-only (discovery + download of already-generated documents, never
# creation/edit/delete of a business record), the same "single view
# permission, no CRUD surface" shape reports:view and dashboard:view
# established for the last two read-only modules - download reuses this
# same code rather than a separate document:download, mirroring how
# reports:view already covers both viewing and exporting a report.
DOCUMENT_VIEW = "document:view"
