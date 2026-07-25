# AquaLedger — Component Library

**The Single Source of Truth for Every Reusable UI Element in AquaLedger**

Version 1.0 · Component Library Specification

This document catalogs every component implied by `01_PRODUCT_VISION.md` through `05_PAGE_CATALOG.md`. It is the frontend's guardrail against reinvention: if a UI need arises during implementation, this catalog is checked first — a new component is only justified per the rules in §19, never as a shortcut.

## How to Read This Catalog

At AquaLedger's scale (~160 components), documenting every field in full prose for every entry would bury the signal. Instead, **each section opens with Category Defaults** — the Accessibility, Keyboard Support, Responsive Behavior, Loading, Error, Empty, and Animation behavior shared by every component in that category, stated once. Each individual component entry below that then documents only what's specific to it: **Purpose, Use When / Avoid When, Variants, Sizes, States, Icons**, plus any **delta** from the category defaults. A component that has no delta from its category defaults simply doesn't repeat them — that silence is intentional, not an omission.

---

## Section 1 — Layout Components

**Category Defaults:** Layout components have no interactive state of their own (no loading/error/empty behavior) — they are structural. Responsive behavior is defined per-component below since layout is precisely where responsive rules diverge most. Accessibility: correct landmark roles (`banner`, `navigation`, `main`, `contentinfo`) are applied at this layer so every page inherits correct document structure without each page reimplementing it.

**App Layout** — The root shell composing Top Navigation + Sidebar + Content Container for every authenticated route. *Use when:* wrapping any page inside the authenticated application. *Avoid when:* Login/Forgot Password/Reset Password/Unauthorized (§1 of `05_PAGE_CATALOG.md`), which render outside this shell entirely. *Variants:* Sidebar-expanded, Sidebar-collapsed (icon rail). *Responsive:* Sidebar variant switches to off-canvas Drawer below the tablet breakpoint, per `03_INFORMATION_ARCHITECTURE.md` §14.

**Sidebar** — The persistent primary-navigation surface (§3 of `03_INFORMATION_ARCHITECTURE.md`). *Use when:* always present in App Layout. *Variants:* Expanded (full labels), Collapsed (icon rail, flyout on hover). *States:* active-route highlight, permission-scoped item visibility. *Keyboard:* fully tab-navigable; expand/collapse toggle has a dedicated shortcut-accessible control. *Responsive:* becomes the mobile Drawer below tablet width.

**Top Navigation** — The persistent topbar: tenant identity, Global Search trigger, theme toggle, Notification Panel trigger, User Menu. *Use when:* always present in App Layout. *Responsive:* condenses to icon-only controls plus a hamburger (Sidebar Drawer trigger) on mobile.

**Page Header** — Title + optional Status Badge + optional Breadcrumb + Primary/Secondary Actions row, per the Page Layout Standard in `05_PAGE_CATALOG.md` §0. *Use when:* top of every List, Detail, and Form page. *Avoid when:* the Dashboard, which uses a lighter header with no breadcrumb (it is the root). *Responsive:* action buttons collapse into an overflow menu below the laptop breakpoint if more than two are present.

**Section Header** — Title + optional short description, introducing a section within a page or form. *Use when:* dividing a Form's field groups or a Detail page's sectioned body. *Avoid when:* the division is already handled by Tabs — a Section Header is not repeated inside each tab's own single-purpose content.

**Content Container** — The max-width-constrained wrapper for page body content, per `02_DESIGN_SYSTEM.md` §5. *Use when:* every page except data-dense List pages, which are the deliberate full-width exception. *Responsive:* max-width relaxes progressively; never causes horizontal scroll at any width.

**Split Layout** — A two-region layout (e.g., a form region beside a live-updating summary region). *Use when:* the Invoice/Purchase Bill Editors' line-items-plus-totals-panel arrangement (see Invoice Line Editor, §10). *Avoid when:* content has no genuine side-by-side relationship — do not use Split Layout merely to fill horizontal space. *Responsive:* regions stack vertically (primary region first) below the laptop breakpoint.

**Dashboard Grid** — The KPI-row-plus-sections grid composing the Executive Dashboard (`05_PAGE_CATALOG.md` §2). *Use when:* Dashboard only. *Responsive:* KPI row reflows 4→2→1 columns; sections stack in the fixed priority order defined in the Dashboard page spec.

**Responsive Grid** — The general-purpose N-column grid underlying Card-based layouts (e.g., a future Entity Card grid view). *Use when:* laying out a collection of Cards rather than tabular data. *Avoid when:* the data is naturally tabular — use Enterprise Data Table (§6) instead; a grid of cards is never used as a substitute for a table merely for visual variety.

**Sticky Footer** — A persistent bottom action bar on long Form pages (e.g., Invoice Editor's Save Draft/Issue actions remaining reachable without scrolling to the form's end). *Use when:* forms whose content can exceed one viewport height. *Avoid when:* short forms (e.g., Create Fish) where the action row is already always visible — an unnecessary sticky footer adds visual noise without benefit.

**Sticky Toolbar** — The List page Toolbar (search/filters/Primary CTA) remaining visible while the table scrolls beneath it. *Use when:* every List page. *Responsive:* remains sticky on mobile, but filters collapse into the drawer trigger described in `05_PAGE_CATALOG.md` §0.

**Resizable Panels** — User-draggable region boundaries. *Use when:* reserved for a future dense-workspace view (e.g., a future side-by-side Trip Catch + Invoice builder); not used anywhere in the current MVP page set. *Future Extension:* the primary candidate for this component once such a workspace view is designed.

---

## Section 2 — Navigation Components

**Category Defaults:** Every navigation component is fully keyboard-operable (arrow keys within a menu/tablist, Enter/Space to activate, Esc to close overlay variants) and exposes current-location state (active/current) to assistive technology via `aria-current`. Loading/Empty/Error behavior does not apply to navigation chrome itself, only to the content it may reveal (e.g., Notification Panel's own empty state, documented under it).

**Sidebar Menu** — The full grouped item list rendered inside Sidebar (§1). *Variants:* grouped-with-headers (Masters/Operations/Finance/etc., per `03_INFORMATION_ARCHITECTURE.md` §3). *States:* item hover, active, permission-hidden (not rendered, not disabled).

**Navigation Group** — A labeled cluster of Menu Items under one section header (e.g., "Finance"). *Use when:* the Sidebar's top-level structure. *States:* expanded/collapsed, per role-based default expansion rules in `03_INFORMATION_ARCHITECTURE.md` §3.

**Menu Item** — A single clickable navigation destination, icon + label. *Use when:* any Sidebar entry, dropdown option, or context-menu row. *Icons:* Lucide, sized per `02_DESIGN_SYSTEM.md` §7, always paired with a text label in primary navigation (icon-only is reserved for well-established cases only).

**Submenu** — A nested Menu Item group (e.g., a future multi-level Settings expansion). *Use when:* a Navigation Group's children themselves need further grouping; not currently required by any module in `03_INFORMATION_ARCHITECTURE.md` §3, whose deepest nesting is Group → Item.

**Breadcrumb** — The clickable path shown on Detail/Edit/Create pages, per `03_INFORMATION_ARCHITECTURE.md` §7. *Use when:* every non-List, non-Dashboard page. *Variants:* full chain (desktop), collapsed "back to parent" (mobile, per `03_INFORMATION_ARCHITECTURE.md` §14). *Rule:* entity names, never raw IDs, are shown as labels.

**Tabs** — Horizontal section switcher within a single record's Detail page (e.g., Trip's Overview/Catches/Expenses/Profit). *Use when:* one entity has multiple related, mutually-exclusive views. *Avoid when:* used as primary page-level navigation — that is the Sidebar's exclusive job, per `03_INFORMATION_ARCHITECTURE.md` §16. *Keyboard:* arrow keys move between tabs, Enter/Space activates.

**Step Navigation** — A numbered sequential-progress indicator for genuinely multi-step processes. *Use when:* reserved for a future guided setup flow; not used by any current page in `05_PAGE_CATALOG.md`. *Avoid when:* faking a single form into "feeling shorter" — per `02_DESIGN_SYSTEM.md` §8's explicit Stepper guidance.

**Pagination** — The paged-results footer control, per `02_DESIGN_SYSTEM.md` §9. *Use when:* every List page's Data Table, every Related Records sub-table. *States:* page-size selector, total-count display, disabled prev/next at boundaries.

**Command Palette** — The `⌘K`/`Ctrl+K` global search-navigate-act surface, per `03_INFORMATION_ARCHITECTURE.md` §12 and `05_PAGE_CATALOG.md` §15. *Use when:* available identically from every page. *Empty behavior:* shows Recent Searches/Recently Visited. *Error behavior:* "No results" state distinct from the empty-query state.

**Global Search** — The same underlying surface as Command Palette, triggered by the topbar search input rather than the keyboard shortcut; documented separately here only because it has a distinct visual trigger point (Top Navigation) — implementation-wise it is one component, not two.

**Quick Actions Menu** — The "+ Quick Create" dropdown of high-frequency Create shortcuts, per `03_INFORMATION_ARCHITECTURE.md` §10. *Variants:* topbar dropdown, Dashboard section (same content, different container). *States:* items permission-scoped per user.

**User Menu** — Avatar-triggered dropdown (Profile, Notification Preferences, Appearance, Logout). *Use when:* Top Navigation, top-right, every page.

**Notification Panel** — The bell-triggered categorized notification feed, per `03_INFORMATION_ARCHITECTURE.md` §11. *States:* unread badge count, per-category grouping. *Empty behavior:* "No notifications" state, distinct from an empty History tab within it. *Loading behavior:* skeleton list matching notification-row shape.

---

## Section 3 — Button Components

**Category Defaults:** Every button variant supports Default/Hover/Pressed/Focus/Disabled states per `02_DESIGN_SYSTEM.md` §3, and two sizes (Default, Small) plus an icon-only sizing mode. Keyboard: focusable via Tab, activates via Enter or Space. Loading behavior: the label is replaced or accompanied by a spinner and the button disables against double-submission, per `02_DESIGN_SYSTEM.md` §8. Animation: press state is near-instant per `02_DESIGN_SYSTEM.md` §14.

**Primary Button** — The single main action on a page/dialog (Save, Issue Invoice, + New Company). *Use when:* exactly one per page/dialog context — never two Primary Buttons competing in the same view. *Avoid when:* the action is destructive — use Danger Button instead even if it's otherwise "the main action."

**Secondary Button** — Supporting actions beside a Primary Button (e.g., Cancel beside Save). *Use when:* any non-primary, non-destructive action.

**Outline Button** — A lighter-weight variant for tertiary actions or dense toolbars where multiple buttons coexist without one dominating. *Use when:* table toolbar actions (Export, Column Selector trigger).

**Ghost Button** — The lowest-emphasis variant, often paired with an icon, for actions embedded within dense content (e.g., a table row's inline action). *Use when:* space-constrained, low-emphasis contexts. *Avoid when:* the action is a page's primary task — Ghost's low visual weight would undersell it.

**Icon Button** — A square, icon-only button. *Use when:* well-established, unambiguous single-purpose actions (close, more-options/kebab, search trigger). *Accessibility:* always carries an accessible label (`aria-label`) even though visually icon-only, per `02_DESIGN_SYSTEM.md` §7.

**Danger Button** — Reserved exclusively for destructive/irreversible actions (Delete, Cancel Trip, Remove Allocation), per `02_DESIGN_SYSTEM.md` §8. *Use when:* paired with a Confirmation/Delete Dialog (§8), never as a page's sole unconfirmed action for anything irreversible.

**Success Button** — A rarely-used affirmative variant (e.g., a future "Approve" action). *Use when:* an explicitly positive, distinct-from-Primary confirmation action exists (approval workflows, roadmap per `01_PRODUCT_VISION.md` §11). *Avoid when:* general "Save" actions — those remain Primary, not Success, to avoid diluting Success's meaning.

**Link Button** — Text-only, no button chrome, used for the lowest-emphasis actions ("Forgot password?", "Cancel" inside a tight dialog footer where an Outline Button would be redundant next to a Primary).

**Loading Button** — Not a separate component but the shared Loading state (category default) applied to any of the above during an async action — documented as its own catalog entry because of how central it is: every Save/Issue/Post/Allocate action in AquaLedger passes through this state.

**Split Button** — A Primary Button paired with an attached dropdown for closely-related alternate actions (e.g., a future "Save Draft ▾" exposing "Save Draft" / "Save & Issue"). *Use when:* two-to-three tightly related action variants exist. *Future Extension:* candidate for the Invoice/Purchase Bill Editor footer once usage data justifies collapsing Save Draft and Issue into one control.

**Dropdown Button** — A button that always opens a menu rather than acting directly (distinct from Split Button, which has a direct default action). *Use when:* the row-level kebab/"⋯" inline actions menu on table rows (§6).

**Floating Action Button** — A persistently-anchored circular primary-action button, common in mobile-first consumer apps. *Avoid when:* essentially always — AquaLedger's Page Header Primary CTA pattern (`05_PAGE_CATALOG.md` §0) is the sole primary-action convention across the product; an FAB would introduce a second, inconsistent pattern. *Included in this catalog explicitly as a component the product does not use*, so it is never introduced ad hoc by mistake.

---

## Section 4 — Form Components

**Category Defaults:** Every form input shares a consistent height/padding/label-placement rhythm (`02_DESIGN_SYSTEM.md` §5), a Default/Hover/Focus/Disabled/Error state set, and inline validation that fires on blur for format checks (per `04_USER_FLOWS.md` §19). Every field has a programmatically associated label (Accessibility default). Loading behavior applies only to async-populated fields (Combobox/Autocomplete/Select variants sourced from the server) — a labeled loading indicator inside the field while options resolve.

**Text Input** — Single-line free text. *Use when:* names, codes, references. *Sizes:* Default, Small (dense table-inline editing contexts).

**Number Input** — Numeric-only entry with right-aligned, tabular-numeral display. *Use when:* quantities, counts. *Validation:* rejects non-numeric characters at the input level, not just on blur.

**Currency Input** — A Number Input variant fixed to the tenant's currency and the backend's exact decimal precision (`NUMERIC(14,2)`), per `02_DESIGN_SYSTEM.md` §4. *Use when:* every money field in the product (rates, amounts, totals) — this is the single most business-critical form component in AquaLedger. *Validation:* never allows entry or display that would round-trip differently than the backend's Decimal value; rejects more decimal places than the field's defined precision rather than silently truncating unseen.

**Percentage Input** — A Number Input variant constrained to 0–100 with a trailing `%` affix. *Use when:* discount %, tax rate fields on Invoice/Purchase Bill lines.

**Email Input** — Text Input with email-format validation on blur. *Use when:* Login, Forgot Password, Create User.

**Phone Input** — Text Input with phone-format validation, optional country-code affix. *Use when:* Company/Supplier contact fields, Boat captain contact.

**Password Input** — Masked text entry with a visibility-toggle affix. *Use when:* Login, Reset Password. *Validation:* strength feedback shown as text (not color alone), per `05_PAGE_CATALOG.md` §1.

**Textarea** — Multi-line free text, sized to expected content length. *Use when:* address fields, future Notes.

**Search Input** — Text Input styled with a search icon affix and (where relevant) a clear-button. *Use when:* every List page Toolbar, Command Palette trigger.

**Combobox** — Type-to-filter single-select from a server- or client-sourced option list, showing selected value once chosen. *Use when:* Fish selector, Company/Supplier selector on Invoice/Purchase Bill lines — AquaLedger's most-used form control by transaction volume. *Loading:* shows a labeled loading state while options resolve; *Empty:* "No matches" state distinct from the loading state.

**Autocomplete** — Functionally the Combobox pattern applied to free-text-with-suggestions contexts (e.g., a future address autocomplete). *Use when:* suggestions augment rather than fully constrain valid input, unlike Combobox where the selection must be one of the offered options.

**Single Select** — A closed-set dropdown (not searchable) for short, fixed option lists (e.g., Company Type: Customer/Supplier/Both). *Use when:* fewer than ~8 options. *Avoid when:* the list is long or server-sourced — use Combobox instead.

**Multi Select** — Select variant allowing multiple choices, each shown as a removable tag within the field. *Use when:* a future multi-category filter; not required by any current single-value field in `05_PAGE_CATALOG.md`.

**Date Picker** — Calendar popover plus direct typed-date entry. *Use when:* Invoice Date, Due Date, Trip dates, boat expiry dates. *Keyboard:* fully typeable without opening the calendar, since data-entry speed matters more than clicking through a calendar for this user base.

**Date Range Picker** — Two-ended Date Picker variant for filter bars (Reports, List page date filters). *Use when:* any "Date Range" filter across the product.

**Time Picker** — Time-of-day entry. *Use when:* reserved for a future precise departure/return timestamp on Trips if date-only proves insufficient; not currently required (Trip dates are date-level per `05_PAGE_CATALOG.md` §7).

**Checkbox** — Independent binary/multi-select choice. *Use when:* table row selection (Bulk Actions), independent form toggles (e.g., a future "notify me" option). *States:* checked/unchecked/indeterminate (header select-all).

**Radio** — Mutually-exclusive choice among visible options. *Use when:* small, always-visible option sets where every choice should be simultaneously scannable (e.g., a future report-type chooser).

**Switch** — Immediate-effect binary setting. *Use when:* theme toggle, Notification Preferences per-category toggles. *Avoid when:* the choice requires an explicit form Save — Switch implies instant effect, per `02_DESIGN_SYSTEM.md` §8.

**Slider** — Continuous-range input. *Avoid when:* essentially always in AquaLedger's current scope — no financial or operational field benefits from imprecise drag-based entry over exact typed entry. *Included explicitly as a non-default component*, per the same rationale as Floating Action Button.

**OTP Input** — Segmented one-time-code entry. *Use when:* reserved for a future two-factor authentication flow; not in the current Authentication Flow (`04_USER_FLOWS.md` §2).

**File Upload** — Drag-or-browse file attachment control. *Use when:* the future Attachments capability on Invoices/Purchase Bills/Trips (`03_INFORMATION_ARCHITECTURE.md` §5, §15). *Future Extension:* the primary interaction surface for the Document Management and OCR roadmap items.

**Image Upload** — File Upload variant with a preview thumbnail. *Use when:* a future tenant-logo/branding field in Company Profile Settings.

---

## Section 5 — Data Display Components

**Category Defaults:** Cards share consistent internal padding and elevation per `02_DESIGN_SYSTEM.md` §5–6. None have their own loading state beyond the page-level skeleton that shapes them (§12); each defines its own empty/error variant only where it displays dynamic content.

**Card** — The base container: surfaced, padded, optionally titled. *Use when:* the default wrapper for any grouped content block not otherwise covered by a more specific card below.

**Stat Card** — A single labeled numeric value with tabular-numeral emphasis. *Use when:* a standalone figure without the fuller KPI Card treatment (trend, click-through). *Relationship:* a simpler sibling of KPI Card (§9), used where a trend/link affordance isn't needed.

**Metric Card** — Synonym-aligned with KPI Card (§9) at the naming-convention level (see §18) — documented fully under Financial Components since every current use of this pattern in AquaLedger is a financial or operational metric.

**Entity Card** — A single-record summary in a card (not row) format — Overview Card content packaged for card-grid contexts. *Use when:* a future card-grid alternative view of a List page (e.g., a visual Boats grid); not the default List page pattern, which remains the Enterprise Data Table (§6).

**Information Card** — A static, non-interactive card presenting reference information (e.g., a help/tips card). *Use when:* rare, non-transactional supporting content.

**Summary Card** — A Card aggregating several related figures (e.g., an Invoice's Totals Panel is a Summary Card variant). *Use when:* Invoice/Purchase Bill Totals Panel, Trip Profit tab summary.

**Status Card** — A Card whose primary content is a Status Badge plus brief supporting context (e.g., a Boat's compliance-status callout). *Use when:* surfacing a single lifecycle/compliance state prominently outside a table row.

**Timeline Card** — The container wrapping a Status Timeline or Audit Timeline (§10) on a Detail page. *Use when:* every Detail page's Timeline/Activity section per `05_PAGE_CATALOG.md` §0.

**Activity Card** — A single entry within an Activity Feed (§10) — one event, its actor, and its timestamp. *Use when:* Recent Activity on the Dashboard, Notification Panel entries.

---

## Section 6 — Table Components

**Category Defaults:** Every table component inherits the standards defined in full in `02_DESIGN_SYSTEM.md` §9 — sortable columns, sticky header, consistent density, keyboard-navigable rows and inline-action menus. Loading state: skeleton rows matching real column structure. Empty state: distinguishes "no data at all" from "no results for current filter," per `04_USER_FLOWS.md` §21.

**Enterprise Data Table** — The single, standardized table implementation underlying every List page and every Related Records sub-table in the product. *Use when:* any tabular collection of records, full stop — this is the one and only table component; no module implements its own table variant.

**Toolbar** — The search+filters+actions row sitting directly above a table, per `05_PAGE_CATALOG.md` §0. *Use when:* every List page.

**Column Selector** — A trigger (typically in the Toolbar) opening a checklist to show/hide table columns. *Use when:* wide, data-dense tables (Invoices, Purchase Bills, Trips) where different roles care about different columns, per `02_DESIGN_SYSTEM.md` §9.

**Bulk Actions** — The contextual action bar that replaces the Toolbar when one or more rows are selected. *Use when:* an entity has a genuine multi-record action (e.g., bulk-deactivate Companies); *Avoid when:* no meaningful bulk action exists for that entity — row selection is not enabled merely for consistency's sake.

**Filter Panel** — The structured-filter portion of the Toolbar (status, date range, entity-reference dropdowns). *Use when:* every List page per its module-specific filter set documented in `05_PAGE_CATALOG.md`.

**Quick Filters** — Single-click filter shortcuts (e.g., a "Compliance expiring soon" chip on Boats) layered in front of the full Filter Panel for the highest-frequency filter combinations. *Use when:* a filter is used often enough to deserve a one-click shortcut beyond the general Filter Panel (Boats' compliance filter, a future "My overdue invoices" saved-view shortcut).

**Search** — The Toolbar's free-text search field (a Search Input instance, §4), scoped explicitly to the fields documented per module in `05_PAGE_CATALOG.md`.

**Sort** — Column-header click-to-sort interaction, one active sort at a time, with a clear direction indicator.

**Pagination** — See Navigation Components (§2); the same component, used at the foot of every table.

**Status Badge** — See Status Components (§7); rendered in a consistent column position on every table showing lifecycle-state entities.

**Row Actions** — The kebab/Dropdown Button (§3) in a table row's final column, offering View/Edit/Delete-or-Deactivate scoped to permission, per `05_PAGE_CATALOG.md` §0.

**Expandable Rows** — A row that reveals nested detail inline without navigating away. *Use when:* reserved for a future dense-review use case (e.g., previewing an invoice's line items from the Invoices list without opening it); not used in the current MVP page set, which favors full navigation to a Detail page for anything beyond the row's own columns.

**Sticky Columns** — The identifying first column (name/number) remaining visible during horizontal scroll on narrow viewports or wide tables, per `02_DESIGN_SYSTEM.md` §15.

**Empty Table** — See Empty States (§13) for the per-entity wording; the structural component is shared across all tables.

**Loading Table** — The Table Skeleton variant (§12) shown while a table's data resolves.

---

## Section 7 — Status Components

**Category Defaults:** Status communication never relies on color alone — every Status Badge carries a text label, satisfying the color-contrast/non-color-dependent accessibility rule in `02_DESIGN_SYSTEM.md` §16. Status vocabularies are closed sets per entity; no entity's status is rendered as free-form text.

**Status Badge** — The base component: a compact, color-coded label representing a closed set of lifecycle values, per `02_DESIGN_SYSTEM.md` §13. Every status-specific "component" below is a **configuration of this one component** with a fixed vocabulary and color mapping — not a separate implementation — which is itself the worked example for the reuse-over-duplication principle in §19.

**Progress Badge** — A Status Badge variant that additionally conveys partial completion (e.g., "Partially Paid," "3 of 5 allocated") — visually a Status Badge with a secondary supporting figure, not a different component family.

**Invoice Status** — Status Badge configured with the vocabulary: Draft, Issued, Partially Paid, Paid, Overdue, Cancelled, per `01_PRODUCT_VISION.md` §6 / `04_USER_FLOWS.md` §11.

**Payment Status** — Status Badge configured for Customer/Supplier Payments: effectively binary in practice (a saved payment is immutable/"Posted"), shown as a single "Posted" badge rather than a multi-state vocabulary, per `04_USER_FLOWS.md` §12.

**Purchase Status** — Status Badge configured with the vocabulary: Draft, Posted, Partially Paid, Paid, per `04_USER_FLOWS.md` §13 — the Purchase Bill mirror of Invoice Status.

**Trip Status** — Status Badge configured with the vocabulary: Planned, At Sea, Returned, Settled, Cancelled, per `04_USER_FLOWS.md` §8.

**Supplier Status** — Status Badge configured with the vocabulary: Active, Inactive.

**Company Status** — Status Badge configured with the vocabulary: Active, Inactive (identical shape to Supplier Status, applied to the Companies master).

**Toast** — Transient, corner-anchored, auto-dismissing (but manually dismissible) confirmation of an action's result. *Use when:* Save/Delete/allocation-adjustment confirmations. *Avoid when:* the information is essential and must not be missable — pair with a persistent Alert or an explicit state change instead (`02_DESIGN_SYSTEM.md` §10).

**Alert** — A persistent, page-embedded message using the semantic color system (e.g., "This invoice is overdue"). *Use when:* content tied to the current page's data, not a transient system event.

**Banner** — A full-width, top-of-page Alert variant for tenant-wide or session-wide messages (e.g., a future maintenance notice). *Use when:* the message applies beyond a single page's content.

**Inline Message** — A small, field- or row-adjacent message (validation errors, a brief inline warning like the boat-compliance-expired notice on Trip creation). *Use when:* the message is scoped to one specific field or table row rather than the whole page.

---

## Section 8 — Feedback Components

**Category Defaults:** Overlay components (Dialog, Drawer, Popover, Tooltip) are elevated per `02_DESIGN_SYSTEM.md` §6, trap or manage focus appropriately while open, close on `Esc` (except mid-destructive-action states), and return focus to their trigger on close.

**Dialog** — The base modal component: focused, blocking task or confirmation, dimmed backdrop. *Use when:* any task that must fully capture attention before the user can continue.

**Confirmation Dialog** — A Dialog variant stating a specific consequence before an action proceeds, per `04_USER_FLOWS.md` §22. *Use when:* every irreversible or hard-to-reverse action across the product (Issue, Post, Cancel, Remove Allocation).

**Delete Dialog** — The Confirmation Dialog variant specifically for record removal, styled with the Danger Button as its primary action. *Use when:* deleting genuinely reversible-in-effect records (draft records, unreferenced masters) per `04_USER_FLOWS.md` §22.

**Success Dialog** — A Dialog variant for confirming a completed multi-step or high-stakes action with a next-step call to action (e.g., a future "Invoice Issued — Send to Customer?" prompt). *Use when:* the action's completion benefits from an explicit next-step offer beyond a Toast; *Avoid when:* a Toast already sufficiently confirms the result (the default for most saves).

**Drawer** — A side-anchored panel for tasks needing more space than a Dialog while preserving page context, and the mobile Sidebar's off-canvas form, per `03_INFORMATION_ARCHITECTURE.md` §14.

**Popover** — Lightweight, click-triggered floating content (a Date Picker's calendar, a quick filter). *Use when:* compact interactive content; distinct from Tooltip by being click- not hover-triggered.

**Tooltip** — Brief, hover/focus-delayed clarification, typically for icon-only controls. *Use when:* the content is supplementary, never the sole carrier of essential information.

**Snackbar** — Treated as the same component as Toast in AquaLedger's system (a naming variant seen in some design systems); documented here to explicitly prevent a second, redundant implementation being introduced under a different name.

**Toast** — See Status Components (§7).

**Skeleton** — See Loading Components (§12).

**Loading Spinner** — A small, indeterminate-wait indicator, used inline (within a Loading Button, within a field awaiting async options) rather than for full-page loads, which use Skeleton instead.

**Progress Bar** — A determinate indicator for multi-step or measurably-long operations (a future bulk import). *Avoid when:* an ordinary page/data load — that's Skeleton's job, per `04_USER_FLOWS.md` §20.

**Empty State** — See Empty States (§13).

**Error State** — See Error States (§14).

**Not Found** — The specific Error State variant for an invalid/inaccessible record ID, per `04_USER_FLOWS.md` §19 and Error States §14 (404).

---

## Section 9 — Financial Components

**Category Defaults:** Every financial component displays values using tabular (fixed-width) numerals at the backend's exact decimal precision, per `02_DESIGN_SYSTEM.md` §4 — this is a hard, non-negotiable rule inherited by every component in this section, not restated per entry below.

**Money Display** — The read-only rendering of a currency value: consistent symbol/placement, fixed decimal places, tabular numerals. *Use when:* any monetary figure shown outside an editable field — table cells, Overview Cards, Totals Panels.

**Currency Input** — See Form Components (§4); the editable counterpart to Money Display.

**KPI Card** — A Metric Card (§5) specialized for Dashboard/Report headline figures: label, large tabular value, optional trend indicator, optional sparkline. *Use when:* Dashboard KPI row, Financial Summary report, Trip Profit tab summary figures.

**Revenue Card** — A KPI Card configured for sales-side totals (e.g., "Total Sales This Period"). *Use when:* Sales Report, Dashboard.

**Outstanding Card** — A KPI Card configured for receivable/payable balances (e.g., "Total Receivables Outstanding"), the Dashboard's most-referenced widget per `05_PAGE_CATALOG.md` §2. *Use when:* Dashboard, Company/Supplier Overview Cards.

**Profit Card** — A KPI Card configured for the Trip Profit tab's Revenue − Expenses = Net Profit summary, per `04_USER_FLOWS.md` §10.

**Expense Card** — A KPI Card configured for aggregate expense figures (e.g., a Trip's total expenses, a future expense-category breakdown).

**Balance Card** — A KPI Card configured for a single entity's running balance (a Payment's Unallocated amount, an Invoice's Balance Due) — the smallest-scope member of this family, often shown inline within a form (the Allocation Table's running total) rather than only at page level.

---

## Section 10 — ERP Components

**Category Defaults:** This section holds AquaLedger's domain-specific components — patterns that exist because of the seafood-ERP business model itself, not generic SaaS UI. Each composes several components from earlier sections rather than introducing wholly new interaction primitives.

**Entity Selector** — A Combobox (§4) preconfigured for a specific entity type (Company, Supplier, Fish, Boat), including that entity's disambiguating context in results (e.g., a Company result showing its outstanding balance). *Use when:* every cross-entity reference field in the product (Invoice's Company field, Trip's Boat field, a line item's Fish field).

**Allocation Table** — The core interaction surface of Customer/Supplier Payment creation: a list of open Invoices/Purchase Bills with an editable per-row allocate-amount field and a running Balance Card showing the unallocated total, per `04_USER_FLOWS.md` §12/§14. *Use when:* Create Payment, Create Supplier Payment, and the Allocation Dialog variant for adding to an existing payment. *Validation:* blocks over-allocation inline, at the offending row, per `04_USER_FLOWS.md` §12.

**Invoice Line Editor** — The dynamic line-items table within the Invoice Editor: Entity Selector (Fish, optionally Trip-Catch-linked), Number Inputs (quantity), Currency Input (rate), Percentage Inputs (discount, tax), and a live Money Display (line total) — composed as a single reusable table pattern, Enter-to-add-row. *Use when:* Create/Edit Invoice only.

**Purchase Line Editor** — The Invoice Line Editor pattern with the Fish/Trip-Catch Entity Selector column omitted, replaced by a free-text description field, per `04_USER_FLOWS.md` §13. *Use when:* Create/Edit Purchase Bill only — a deliberate, minimal variant of Invoice Line Editor rather than a wholly separate implementation.

**Status Timeline** — A vertical chronological list of an entity's lifecycle transitions (Draft→Issued→Paid, etc.), each entry showing the transition, actor, and timestamp. *Use when:* every Finance-lifecycle Detail page's Timeline tab/section, Trip Details' Timeline.

**Audit Timeline** — The Status Timeline pattern extended with full before/after field-level change detail, used specifically for the Audit Logs detail view (`05_PAGE_CATALOG.md` §13) — a superset of Status Timeline's content, not a different visual pattern.

**Activity Feed** — A reverse-chronological list of Activity Cards (§5) spanning multiple entities (as opposed to Status Timeline's single-entity scope). *Use when:* Dashboard Recent Activity, Notification Panel History.

**Quick Filter Bar** — See Quick Filters (§6); documented under both sections because it sits structurally within Table Components but is a domain-specific pattern (e.g., "Compliance expiring soon") worth cross-referencing here.

**Advanced Filter Builder** — A structured multi-condition filter constructor beyond the default Filter Panel's fixed field set. *Use when:* reserved for a future power-user Reports capability; not required by any current List page, whose Filter Panel set is fixed and sufficient per `05_PAGE_CATALOG.md`.

---

## Section 11 — Chart Components

**Category Defaults:** All charts use Recharts, per `02_DESIGN_SYSTEM.md` §11, with a consistent series-color mapping, tabular-numeral axis/tooltip formatting, and dark/light-theme-tuned palettes (`02_DESIGN_SYSTEM.md` §17). None have a distinct "error state" beyond the standard page-level Error State — a failed chart data load surfaces the same Alert-with-Retry pattern as any other section.

**Line Chart** — Trend over time. *Use when:* Dashboard revenue trend, Sales/Purchase Report trends.

**Area Chart** — A Line Chart variant emphasizing cumulative/volume. *Use when:* sparingly, only where emphasis genuinely benefits from the filled treatment — per `02_DESIGN_SYSTEM.md` §11's caution against overuse.

**Bar Chart** — Comparison across discrete categories. *Use when:* Dashboard receivables aging, Sales by Fish/Category breakdowns.

**Pie Chart** — Composition of a whole, five-or-fewer categories. *Avoid when:* more than roughly five categories or when a bar chart/table would read more precisely — per `02_DESIGN_SYSTEM.md` §11.

**Donut Chart** — A Pie Chart variant with a center label (often the total). *Use when:* the same constraints as Pie Chart, where a center-anchored total figure adds value.

**KPI Widgets** — See KPI Card (§9); the chart-adjacent term for the same component when discussed in a charting context.

**Trend Card** — A KPI Card with an embedded Sparkline (below) rather than a full chart, for compact trend context without dedicating a full chart's visual weight.

**Sparkline** — A minimal, axis-less inline trend line. *Use when:* embedded within a Trend Card or table cell to show a compact history at a glance. *Avoid when:* the trend needs to be read precisely — a Sparkline is for gestalt pattern recognition only, never a substitute for a full Line Chart when exact values matter.

---

## Section 12 — Loading Components

**Category Defaults:** Every skeleton variant shows immediately (no delay-before-appearing), matches the real content's approximate shape and rhythm, and is replaced the instant real content is available with no artificial minimum display duration, per `04_USER_FLOWS.md` §20.

**Page Skeleton** — The composite skeleton for an entire page's initial load, assembled from the section-specific skeletons below rather than a single generic placeholder.

**Card Skeleton** — Placeholder shape for any Card variant (§5) while its content resolves.

**Table Skeleton** — Placeholder rows matching the real table's column structure, per `02_DESIGN_SYSTEM.md` §9 / `05_PAGE_CATALOG.md` §0 List Page Template.

**Chart Skeleton** — A placeholder shape approximating the eventual chart's axes/plot area.

**Form Skeleton** — Placeholder field shapes matching an Edit page's field layout while the existing record loads (Create pages have no server dependency and so render immediately, per `05_PAGE_CATALOG.md` §0 Form Page Template).

**Dashboard Skeleton** — The Page Skeleton composition specific to the Dashboard's independently-loading sections (KPIs, Charts, Activity, Pending Work, Outstanding), per `05_PAGE_CATALOG.md` §2 — each section skeletons and resolves independently rather than the page blocking on the slowest one.

---

## Section 13 — Empty States

**Category Defaults:** Every Empty State is purposeful and action-oriented (a short explanation plus the module's own Primary CTA where creation is the natural next step), distinguished clearly from "No Search Results" (which offers a clear-filters action instead) and from Error State (a failure, not an absence), per `04_USER_FLOWS.md` §21.

**No Companies / No Suppliers / No Fish / No Boats / No Trips / No Invoices / No Purchase Bills / No Payments** — Each module's List page Empty State: brief entity-specific copy plus the module's "+ New [Entity]" action. *Use when:* the module genuinely has zero records for this tenant (typically only during initial onboarding). *Note:* documented as one pattern with per-module copy, not eight separate components.

**No Reports** — The "Coming Soon" variant used for the Reports module and any other not-yet-shipped destination (`04_USER_FLOWS.md` §21), distinct from the standard No-Data pattern in that it communicates a roadmap state rather than an empty-but-available module.

**No Search Results** — The shared variant used across every List page's Search/Filter and the Command Palette (§2), stating no matches were found and offering a clear-filters/clear-search action.

**Offline** — A persistent, low-key connectivity-lost indicator (not a full-page blocking state), disabling network-dependent actions inline with an explanation rather than allowing them to fail silently, per `04_USER_FLOWS.md` §21.

---

## Section 14 — Error States

**Category Defaults:** Every error surfaces without exposing raw internal exception detail, per `01_PRODUCT_VISION.md`'s API standard, and offers Retry wherever the failure is plausibly transient (never for validation/permission failures, which would simply fail again identically), per `04_USER_FLOWS.md` §19.

**403 (Permission Error)** — Rendered as the Unauthorized page (`05_PAGE_CATALOG.md` §1) for full-route access, or an inline Alert for an action-level defensive check.

**404 (Not Found)** — A dedicated "this record doesn't exist or you don't have access" page for an invalid Detail-page ID, deliberately not distinguishing the two causes, per `04_USER_FLOWS.md` §19.

**409 (Conflict)** — An inline error explaining a concurrent-state conflict (e.g., allocating against an invoice another session just fully paid), with the affected data auto-refreshed before retry.

**422 (Validation Error)** — Field-level inline errors mapping server-side validation failures back to their specific field, matching the same visual treatment as client-side inline validation.

**500 (Server Error)** — A generic, honest page- or section-level Alert ("Something went wrong on our end") with Retry and an optional trace/reference identifier.

**Network Error** — A page- or action-level Alert ("Couldn't reach the server — check your connection") with Retry; in-progress form data is always preserved, never cleared by a failed submission.

**Timeout** — Treated identically to Network Error in presentation (the user cannot distinguish the two meaningfully); Retry offered identically.

**Retry** — Not a distinct visual state but the shared action affordance attached to every transient-failure Alert above — documented as its own entry because of how consistently it must behave: same label, same placement, same behavior (re-attempts the exact failed operation) everywhere it appears.

---

## Section 15 — Accessibility

Accessibility is not a per-component feature toggle in AquaLedger — it is a property every component in this catalog inherits by construction, per `02_DESIGN_SYSTEM.md` §16:

- **Keyboard Navigation** — every interactive component (buttons, form fields, table rows and their action menus, tabs, the Command Palette, dialogs) is fully operable via keyboard alone with a logical tab order; this is stated once here rather than repeated in every component entry above, and any component whose keyboard behavior diverges from the obvious default says so explicitly in its own entry (e.g., Date Picker's typeable-without-opening behavior).
- **ARIA** — semantic roles/states/labels are applied consistently per component *type*, not per instance — every Status Badge, every Dialog, every Data Table exposes identical ARIA structure regardless of which page it appears on.
- **Focus Management** — overlay components (Dialog, Drawer, Command Palette) manage focus on open/close per the Section 8 category default; page-level navigation moves focus to the new page's primary heading.
- **Screen Readers** — dynamic content changes (Toast appearing, inline validation firing, a table row updating after an action) are announced, not just visually updated.
- **Color Contrast** — every color pairing used by any component in this catalog meets WCAG AA at minimum, in both themes, per `02_DESIGN_SYSTEM.md` §3/§16.
- **Reduced Motion** — every Animation behavior referenced throughout this catalog degrades to an instant or near-instant equivalent when the user's reduced-motion preference is set, per `02_DESIGN_SYSTEM.md` §14/§16, with no loss of the information that motion was communicating (e.g., a Drawer still appears/disappears, just without the slide transition).

---

## Section 16 — Responsive Behavior

Component-level responsive rules are inherited from the page-level rules defined in `05_PAGE_CATALOG.md` §16 and `02_DESIGN_SYSTEM.md` §15, applied consistently by component type rather than reinvented per page:

- **Desktop / Laptop** — full component set at full fidelity; multi-column Form field groups, full Sidebar, full Data Table column set.
- **Tablet** — Sidebar collapses to icon rail or Drawer; Split Layout and multi-column Forms collapse to single column; Data Table gains horizontal scroll with Sticky Columns.
- **Mobile** — Sidebar becomes a full Drawer; Top Navigation condenses to icon controls plus hamburger; Dialogs and Drawers become full-width/full-height overlays; Data Table retains horizontal scroll rather than restructuring into stacked cards, preserving the same mental model at every width, per `04_USER_FLOWS.md` §24.

No component in this catalog defines a bespoke mobile treatment outside these shared rules, for the same reason stated in `05_PAGE_CATALOG.md` §16: consistency across ~160 components is only tractable if responsive behavior is a property of the *category*, not reinvented per component.

---

## Section 17 — Component Composition

Components are never used in isolation — every page in `05_PAGE_CATALOG.md` is a specific composition of the primitives above. Three representative compositions:

```
List Page
  Page Header (§1)
        ↓
  Toolbar (§6) — Search (§6) + Filter Panel (§6) + Primary Button (§3)
        ↓
  Enterprise Data Table (§6) — Status Badge (§7) columns, Row Actions (§3/§6)
        ↓
  Pagination (§2/§6)
```

```
Invoice Editor
  Page Header (§1) — Invoice Status Badge (§7)
        ↓
  Entity Selector (§10) — Company
        ↓
  Invoice Line Editor (§10) — Entity Selector + Number/Currency/Percentage Inputs (§4)
        ↓
  Summary Card (§5) — Totals Panel, Money Display (§9) throughout
        ↓
  Sticky Footer (§1) — Secondary Button (Save Draft) + Primary Button (Issue)
        ↓
  Confirmation Dialog (§8) — on Issue
```

```
Dashboard
  Dashboard Grid (§1)
        ↓
  KPI Card / Outstanding Card (§9) row
        ↓
  Line Chart / Bar Chart (§11)
        ↓
  Enterprise Data Table (§6) — Pending Work, in compact form
        ↓
  Activity Feed (§10) — Activity Card (§5) list
```

This is the intended reading of the entire catalog: no page introduces a component not already defined above, and every page can be described, as shown, as a specific ordered stack of these ~160 primitives.

---

## Section 18 — Naming Conventions

The canonical name for every component is the one used as its heading in Sections 1–14 above, and it is used identically in design files, this documentation, and eventual code — no synonyms:

- **Button variants** are always named `[Variant] Button` (Primary Button, Danger Button) — never "the blue button" or "the delete button" in any design or engineering conversation.
- **Cards** are always named `[Purpose] Card` (KPI Card, Summary Card, Status Card) — a card's name states what it's *for*, not what it *looks like*.
- **Status-vocabulary components** (Invoice Status, Trip Status, etc.) are named `[Entity] Status` and are always understood as configurations of the single Status Badge component (§7), never described or built as independent components.
- **Domain-specific (ERP) components** (§10) are named for the business concept they represent (Allocation Table, Invoice Line Editor), not for their generic UI shape (never "the payment grid" or "the line-item form") — this mirrors the entity-naming discipline established in `03_INFORMATION_ARCHITECTURE.md` §18.
- **Skeletons** are always named `[Target] Skeleton` (Table Skeleton, Card Skeleton) and are understood as the loading-state counterpart of the component they name, not a separate component family.

---

## Section 19 — Design Rules

**When to reuse (the default, almost-always answer):** If a UI need can be met by an existing component from this catalog — including a documented *variant* of one — it must be. Reaching for an existing Combobox, Card, or Dialog variant is always the first move, not the last resort.

**When to create a new component (the narrow exception):** A new component is justified only when **all** of the following are true:
1. The need cannot be met by any existing component or a documented variant/configuration of one (per the Status Badge → Invoice Status pattern in §7, which shows how far configuration alone should be pushed before reaching for a new component).
2. The need will recur across more than one page (a genuinely one-off layout need is solved locally within that page's composition, per §17, not promoted to a catalog entry).
3. The new component can be specified against the same field set as every entry above (Purpose, Use When/Avoid When, Variants, States, Accessibility, etc.) — if it can't be cleanly specified this way, it's a sign the need should be decomposed into existing primitives instead.

**Avoid duplication:** Before building, check whether the need is actually a *variant* of something already cataloged (e.g., Purchase Line Editor is a variant of Invoice Line Editor, not a new component) rather than a wholly new pattern. The majority of AquaLedger's ~160 entries above are variants/configurations of a much smaller set of true primitives (Button, Card, Input, Table, Dialog, Status Badge) — that ratio is intentional and should be preserved as the product grows.

**Maintain consistency:** Any change to a component's behavior (a new Button state, a new Table density option) is made once, at the component level, and propagates to every page using it — never patched into one page's local copy. If a page seems to need a component to behave differently than its catalog definition, that's a signal to either add a documented Variant (updating this catalog) or reconsider whether the page's design should change instead — not to fork the component silently.

---

## Section 20 — Summary

AquaLedger's component library is built on a small set of true primitives — Button, Input, Card, Table, Dialog, Status Badge, and a handful of domain-specific ERP patterns — from which everything else in this ~160-entry catalog is a documented variant or configuration. This is what makes the library **scalable**: a new module (Reports' remaining report types, future Documents/OCR/AI surfaces per `01_PRODUCT_VISION.md` §11) is built almost entirely from components that already exist, needing at most a handful of genuinely new, narrowly-justified additions per §19.

It is **maintainable** because behavior lives at the component level, not duplicated per page — a correctness fix to Currency Input's decimal handling, for instance, fixes every money field in the product simultaneously, which matters enormously given how central financial exactness is to this product's entire value proposition (`01_PRODUCT_VISION.md` §1).

It is **consistent** for the same reason the naming conventions in §18 exist: one name, one component, one behavior, everywhere — a user who has learned to use the Allocation Table on a Customer Payment already knows the Supplier Payment screen, and a developer who has implemented the Invoice Line Editor has, by construction, already implemented most of the Purchase Line Editor. Combined with `05_PAGE_CATALOG.md`'s page templates, this catalog completes the chain from product vision to pixel: every business rule in `01_PRODUCT_VISION.md` flows through a navigation structure (`03_INFORMATION_ARCHITECTURE.md`), a set of user journeys (`04_USER_FLOWS.md`), a page (`05_PAGE_CATALOG.md`), and finally into one of the ~160 standardized components documented here — with no gap left for ad hoc invention at implementation time.
