# AquaLedger — Design System

**The Official Visual & Interaction Language for AquaLedger**

Version 1.0 · Design System Specification · Single Source of Truth for Design & Frontend

This document translates the Product Vision (`01_PRODUCT_VISION.md`) into a concrete, unambiguous design language. It is conceptual and framework-agnostic by design — no hex values, no CSS, no component code — so it can outlive any single implementation while still being precise enough that two different developers building the same screen would arrive at visually identical results.

---

## 1. Design Philosophy

AquaLedger's UI is a **precision financial instrument that happens to be beautiful**, not a decorative interface that happens to hold financial data. Every visual decision is subordinate to one question: does this help someone enter data faster, read a number more confidently, or understand system state more quickly?

The product should feel:

- **Professional** — the visual register of a tool people trust with money and compliance, not a consumer app.
- **Modern** — current 2026 SaaS craft: restrained color, purposeful whitespace, sharp typography — not last decade's flat-design or this decade's over-decorated glassmorphism either.
- **Minimal** — nothing on screen that doesn't earn its place; density comes from information, not ornamentation.
- **Elegant** — quiet confidence. Elegance here means *removing* friction and visual noise, not adding polish.
- **Fast** — the UI must *look* as fast as it *is* — instant-feeling transitions, no gratuitous animation standing between the user and their next action.
- **Enterprise** — multi-tenant, role-aware, audit-conscious; the interface should visibly earn the trust of a business that will run its books through it.
- **Trustworthy** — numbers are never ambiguous, states are never unclear, destructive actions are never one accidental click away.
- **Financial** — exactness is a visual value, not just a backend guarantee: aligned figures, unambiguous currency, disciplined use of color for financial meaning (never decorative).
- **Operational** — built for people who live in this tool for hours a day, entering trips, invoices, and payments — optimized for repeat, high-volume use, not first-impression marketing polish.
- **Accessible** — usable by everyone on the team, in either theme, regardless of vision or motor ability.

The governing test for every design decision in this system: **would this look at home in Linear, Stripe Dashboard, Mercury, Ramp, Vercel, Notion, or GitHub?** If a pattern instead evokes a Bootstrap admin template or a legacy on-premise ERP, it is wrong for AquaLedger, regardless of how conventional it is in ERP software generally.

---

## 2. Brand Identity

**Brand Personality:** Precise, calm, capable. AquaLedger behaves like a senior accountant who never panics and never makes an arithmetic error — steady under pressure, quietly confident, never flashy.

**Visual Tone:** Restrained and structured. Cool, neutral surfaces let data be the visual content; a single, deliberate accent color is reserved for meaningful action and identity, never scattered decoratively across the interface.

**Emotional Goals:** Users should feel *in control*, not *managed by* the software. A trader entering their fortieth invoice of the day should feel the same calm confidence as on their first. Financial correctness should feel like a property of the room, not something the user has to actively verify.

**Voice:** Direct, plain-language, respectful of the user's expertise. Copy in the product (labels, empty states, confirmations, errors) is written the way a competent colleague would speak — no jargon-for-its-own-sake, no forced friendliness, no scolding tone on errors. Confirmation and warning copy states consequences plainly ("This invoice will be locked and cannot be edited after issuing") rather than vaguely ("Are you sure?").

**Product Identity:** AquaLedger's identity draws a quiet line to its domain — ocean/maritime association — without ever becoming literal or thematic. No wave motifs, no fish iconography beyond what's functionally necessary (e.g., a fish icon in navigation), no nautical decoration. The seafood-industry connection lives in the *content* and *workflows* of the product, not in its chrome.

**How Users Should Feel:** Efficient, respected, and unhurried-but-fast — like using a tool built specifically for how they already think about their business, rather than a generic system they've had to adapt themselves to.

---

## 3. Color System

Color in AquaLedger is a **functional signaling system first, an aesthetic choice second.** Every color used must be traceable to a purpose: identity, state, hierarchy, or feedback. Decorative color is not used.

### Palette Roles

- **Primary** — the single brand/action color. Used sparingly and consistently: primary buttons, active navigation state, key links, focus rings, brand touchpoints. Should read as confident and specific to AquaLedger (a maritime-adjacent, professional hue), never generic corporate blue.
- **Secondary** — a muted companion to primary, used for secondary emphasis where primary would be too loud (secondary buttons, subtle highlights).
- **Accent** — a sparingly-used complementary color reserved for rare moments that must stand out distinctly from primary (e.g., a "new" indicator), used far less often than Primary.
- **Success** — positive financial/operational states: paid, cleared, completed, active.
- **Warning** — attention-needed but not broken: partially paid, pending, nearing a threshold (e.g., a boat license expiring soon).
- **Danger** — negative or destructive states and actions: overdue, cancelled, delete actions, validation failures.
- **Info** — neutral informational emphasis: helper callouts, informational badges, non-urgent notifications.
- **Neutral / Gray Scale** — the workhorse of the interface. A full, evenly-stepped neutral ramp carries text, borders, backgrounds, and disabled states — this palette does more visual work than every other color combined, consistent with a data-dense, low-decoration product.

### Surfaces & Backgrounds

- A layered surface model: **base background** (the canvas), **raised surface** (cards, tables, panels), and **overlay surface** (dialogs, popovers, dropdowns) — each a subtly distinct step in the neutral ramp so elevation is legible even before shadow is considered.
- Backgrounds stay strictly neutral; color is never used to tint a background for decoration.

### Borders

- A single low-contrast neutral border color is used for structural division (table rows, card edges, input outlines) in its resting state.
- Borders step up in contrast/color only to communicate state: focus (primary), error (danger), or an actively-hovered/selected row.

### Dark Theme & Light Theme

- Both themes are **first-class**, designed together, not one derived mechanically from the other.
- **Light theme** uses soft off-white surfaces (never pure white) and near-black (never pure black) text, keeping contrast high without harshness.
- **Dark theme** uses deep, desaturated neutral surfaces (never pure black) with softened, slightly desaturated versions of every semantic color, so Success/Warning/Danger remain legible and correctly-weighted rather than glowing or oversaturated against a dark canvas.
- Every semantic color (Primary, Success, Warning, Danger, Info) has a defined light-theme value and dark-theme value that preserve the same *meaning* and relative *prominence* in both themes — dark mode is not simply an inverted light mode.
- All theme pairs meet WCAG AA contrast for text and meaningful UI elements at minimum.

### State Colors

Every interactive element defines a consistent set of state treatments, applied system-wide rather than invented per component:

- **Default (resting)** — the element's baseline appearance.
- **Hover** — a subtle shift (typically a small step up in surface/border contrast or a light tint of the element's own color) signaling interactivity without being loud.
- **Pressed / Active** — a slightly stronger version of the hover treatment, giving tactile confirmation of a click before the action resolves.
- **Focus** — a clear, consistent focus ring (using the Primary color) on every interactive element, visible identically whether reached by mouse or keyboard — never suppressed for aesthetic reasons.
- **Disabled** — reduced contrast/opacity and removal of interactive affordances (no hover/pressed states fire), always paired with a reason communicated elsewhere (tooltip, helper text) rather than a disabled control with no explanation.
- **Selected** — a distinct, persistent treatment (not just a momentary hover/press) for rows, options, or tabs currently chosen, using a light Primary tint.

---

## 4. Typography

**Font Families:** A single modern, highly-legible grotesque/sans-serif typeface family (in the vein of Inter or Geist) is used for all UI text — headings, body, labels, tables — to keep the interface feeling unified and native to 2026 SaaS conventions. A companion monospace family is used exclusively where tabular/numeric alignment matters.

**Heading Scale:** A small, disciplined scale (page title → section heading → card/subsection heading) — three to four steps, each with a clear, consistent size and weight relationship to the next. Headings are used to establish hierarchy, never for decoration or emphasis outside their structural role.

**Body Text:** One primary body size for all standard reading and form content, sized for comfortable extended use (this is a tool people read for hours), with a secondary smaller size reserved for dense table content where appropriate.

**Captions & Labels:** A smaller, often medium-weight or muted-color style for form field labels, table column headers, and metadata (timestamps, "created by," helper text) — always legible, never so small it undermines accessibility.

**Tables:** Table body text favors clarity and alignment over size — typically the same as or one step below body text, with column headers visually distinct (weight or color, not necessarily size) from row content.

**Monospace Usage:** Reserved specifically for **numeric and identifier content that benefits from fixed-width alignment**: money amounts, quantities, rates, invoice/bill numbers, GSTIN and other codes. Never used for prose.

**Number Formatting:** All monetary, quantity, and rate figures use **tabular (fixed-width) numerals** so that columns of numbers in tables and totals panels align vertically digit-by-digit — this is a hard requirement, not a stylistic preference, given how much of the product is columns of numbers.

**Financial Formatting:** Currency values always display with a consistent, locale-appropriate symbol/placement and a fixed number of decimal places matching the backend's `NUMERIC(14,2)` precision; quantities follow the backend's weight precision; rates follow the backend's rate precision. The UI never rounds or truncates differently than the backend computed — displayed figures are always a faithful, exact representation of the underlying Decimal value.

---

## 5. Spacing System

**Grid:** A consistent base spacing unit underlies all layout decisions, with a small set of multiples of that unit used system-wide (no arbitrary one-off spacing values). This creates rhythm that makes the interface feel machine-precise rather than hand-tuned per screen.

**Container Width:** Content areas use a constrained maximum width on large displays to keep line lengths and table widths readable, rather than stretching every screen edge-to-edge on ultrawide monitors; data-dense screens (large tables) are the deliberate exception, allowed to use available width.

**Section Spacing:** Generous, consistent vertical rhythm between major page sections (header → filters → table → pagination) so the eye can parse a page's structure at a glance.

**Card Spacing:** Consistent internal padding for cards and panels, scaled slightly by content density (a KPI card uses more breathing room than a dense data card), but never ad hoc per instance.

**Form Spacing:** Consistent vertical spacing between form fields and between field groups/sections, with tighter spacing between a label and its input than between one field and the next, so visual grouping matches logical grouping.

**Button Spacing:** Consistent internal padding scaled to button size (default/small/large), and a consistent gap between buttons grouped in an action bar or dialog footer.

**Responsive Spacing:** Spacing compresses in a controlled, predictable way at narrower breakpoints (tighter section and card padding) rather than each screen inventing its own mobile behavior.

---

## 6. Elevation

Elevation communicates **layering, not decoration** — it tells the user what is "above" what, and what will disappear if they click away.

- **Cards / Panels** — resting content, minimal or no shadow; separation from background comes primarily from the surface-color step described in Section 3, with a subtle shadow as secondary reinforcement.
- **Dropdowns / Menus / Popovers / Tooltips** — a light, tight shadow — enough to read as "floating just above the page," dismissed easily and expected to be transient.
- **Dialogs / Modals** — a stronger, more diffuse shadow paired with a dimmed backdrop over the rest of the page, clearly communicating a modal, attention-demanding state.
- **Drawers / Floating Panels** — similar weight to dialogs when they block interaction with the rest of the page; lighter when they coexist with page interaction.

**Border Radius:** A small, consistent set of radius values (not a continuous range) mapped to component scale — small controls (badges, inputs, buttons) use a tighter radius; larger containers (cards, dialogs) use a slightly more generous one. Radius stays moderate throughout — enough to feel modern and soft, never so rounded it reads as playful or consumer-grade.

**Depth Hierarchy:** At any moment, the number of simultaneously "elevated" layers is kept small and predictable (e.g., page → dialog → its own dropdown, at most) so the user is never uncertain what layer they're interacting with.

---

## 7. Icons

**System:** Lucide Icons, used exclusively — a single, consistent outlined icon set across the entire product. No mixing of icon styles or sources.

**Philosophy:** Icons are a *functional aid to recognition and scanning*, never decoration. Every icon used must pair with or reinforce a text label in primary navigation and actions — icon-only usage is reserved for extremely well-established, unambiguous cases (search, close, more-options, notification bell) and always carries an accessible label even when visually icon-only.

**Sizing:** A small fixed set of icon sizes is used system-wide, each tied to a specific context (inline with body text, inline with a button label, standalone in a sidebar or toolbar) — never arbitrarily sized per instance.

**Usage:** Consistent stroke weight and visual weight across all icons at a given size, so the icon set reads as one coherent family rather than a collection of individually-chosen symbols. Icon color follows the same semantic system as text/borders — neutral by default, semantic color only when the icon itself is communicating state (e.g., a warning triangle).

**Consistency:** The same concept is always represented by the same icon everywhere in the product (e.g., the icon used for "edit" is never swapped for a different pencil-like icon on a different screen).

---

## 8. Component Standards

Every component below is a **standardized pattern**, not a one-off design. The same component looks and behaves identically everywhere it appears, regardless of which module it's used in.

**Buttons** — A small set of variants (Primary, Secondary, Outline/Ghost, Danger) each with a fixed visual treatment and clear purpose: Primary for the single main action on a screen, Secondary/Outline for supporting actions, Danger reserved exclusively for destructive actions. A small set of sizes (default, small, icon-only). Every button has defined resting/hover/pressed/disabled/focus states per Section 3, and a loading state (spinner replacing or accompanying the label) for async actions.

**Inputs (Text, Number, Textarea)** — Consistent height, padding, border, and label placement across all text-entry fields. Number inputs used for money/quantity/rate always right-align content and reserve space for tabular alignment. Textarea follows the same visual language as text inputs, sized for its expected content length.

**Select / Multi Select** — Visually consistent with text inputs at rest; opens a menu styled per the Dropdown/Menu elevation standard. Multi Select shows chosen values as compact tags within the field, with a clear, individually-removable affordance per tag.

**Date Picker / Date Range** — A calendar popover consistent with other popovers in elevation and radius; supports direct typed entry as well as calendar selection, since this is a data-entry-heavy tool where typing is often faster than clicking.

**Checkbox / Radio / Switch** — Distinct, purpose-matched controls: Checkbox for independent multi-select choices, Radio for mutually exclusive choices, Switch for immediate-effect binary settings (not for form fields requiring an explicit Save). Consistent sizing and a clear checked/unchecked/indeterminate (checkbox only) visual language.

**Combobox / Autocomplete / Search** — A unified pattern for "type to filter a list and select" interactions (used heavily for Company, Fish, and Trip Catch selection in forms) — consistent affordance for showing available options, loading state while searching, and a clear empty-results state.

**Badges / Tags / Status Badge** — Badges are compact, color-coded per Section 13's status system, used for lifecycle state. Tags are neutral-styled, used for free-form categorization/labels rather than system state — the two are visually distinct so a user never confuses "this is a status" with "this is a label."

**Cards** — The standard container for grouped content (a summary panel, a KPI, a settings section), following the elevation and spacing standards above.

**Tabs** — Used to divide a single entity's detail view into related sections (e.g., a Trip's Overview/Catches/Expenses), never used as primary page-level navigation (that's the sidebar's job).

**Accordion** — Reserved for progressive disclosure of optional/secondary detail (e.g., advanced filters, long help content), not for primary content that should always be visible.

**Avatar** — Consistent circular treatment for user identity, with a defined fallback (initials) when no image is present, used in the topbar user menu and anywhere a specific person (e.g., "created by") is referenced.

**Breadcrumb** — Present on all detail/edit pages, showing the path from module root to the current record, each segment clickable except the current page.

**Pagination** — A consistent control for paged tables/lists, always paired with a visible total-count indicator, appearing identically across every list page in the product.

**Stepper** — Reserved for genuinely sequential multi-step processes (e.g., a future guided setup flow), not used to fake a single form into "feeling shorter."

**Timeline** — Used for chronological/audit-style views (e.g., a record's history of status changes), visually distinct from a table when the emphasis is sequence-over-time rather than comparable rows.

**Alerts** — Persistent, page-embedded messages (e.g., "This invoice is overdue") using the semantic color system, distinct from Toasts by being tied to page content rather than a transient system event.

**Toast** — Transient, corner-anchored notifications for the result of an action (saved, error, etc.), auto-dismissing but always also manually dismissible, never used for information the user must act on (that's a Dialog's job).

**Tooltip** — Brief, delayed-on-hover clarification for icon-only controls or truncated content; never contains the only copy of essential information.

**Popover** — Lightweight floating content triggered by a click (not hover), used for compact interactive content (e.g., a quick filter, a date picker) — styled per the Dropdown elevation standard.

**Dialog / Modal** — Reserved for focused, blocking tasks and confirmations; always has a clear title, a clear primary action, and a clear dismiss path (explicit Cancel plus an escape/backdrop-click affordance where the action isn't destructive-in-progress).

**Drawer** — A side-anchored alternative to a Dialog, used when the task benefits from more space or from keeping page context partially visible (and for mobile navigation, per `DESIGN_PROMPT.md`'s slide-out nav pattern).

**Context Menu** — Right-click or kebab-triggered action lists on table rows and cards, using the same menu styling as Dropdowns for consistency.

**Progress / Loading Spinner / Skeleton Loader** — Progress bars for determinate multi-step or long-running processes; spinners for short indeterminate waits (inline, e.g., a button's own loading state); skeleton loaders for initial page/section content loads, shaped to approximate the real content's layout so the page doesn't visually "jump" once data arrives.

**Metric Card / KPI Card** — A standardized dashboard building block: a label, a large tabular-numeral value, an optional trend indicator, and optional supporting context — consistent across every metric shown anywhere in the product.

**Charts** — See Section 11.

**Tables / Filters / Search Bar** — See Section 9.

**Global Search / Command Palette** — A single, consistent ⌘K-triggered palette for cross-entity search and quick navigation/actions, styled per the Dialog/overlay elevation standard, available identically from anywhere in the product.

**Action Bar** — A consistent placement and styling for a page's primary and secondary actions (typically top-right of a page header), so users always know where to look for "the main thing I can do here."

**Empty State / Error State / Success State / Loading State** — Every list, table, and data-dependent view defines all four states explicitly and consistently: a friendly, action-oriented empty state (not just blank space), a clear error state with a retry path, a success confirmation where relevant, and a skeleton-based loading state — no view is designed for only its "happy path."

**Confirmation Dialog / Delete Dialog** — A standardized pattern for any irreversible or hard-to-reverse action, always stating the specific consequence in plain language (not a generic "are you sure?"), with the destructive action styled in the Danger button variant and never the visually primary/pre-focused button.

**Form Layout / Section Header / Page Header** — Standardized structural components used on every page and form: Page Header (title, optional breadcrumb, status badge where relevant, action bar), Section Header (a form or content section's title, optionally with a short description), and a consistent Form Layout grid for label/input arrangement across every form in the product.

---

## 9. Table Design

Tables are the most-used surface in AquaLedger and are held to the highest standard of consistency in the system.

- **Sorting** — Any column that represents a meaningfully orderable value (date, amount, status, name) is sortable via a consistent header-click interaction, with a clear indicator of current sort column and direction.
- **Filtering** — A consistent filter bar sits directly above every data table: free-text search plus a small set of the most relevant structured filters (status, date range, counterparty) for that entity — never a generic "filter" button hiding the entire interaction behind an extra click for the filters used constantly.
- **Pagination** — Every table paginates rather than infinite-scrolls, with a consistent page-size control and total-count display, so financial data always has a countable, citable boundary ("showing 1–50 of 240").
- **Sticky Header** — Column headers remain visible while scrolling through long tables, so context is never lost.
- **Column Resizing** — Supported on data-dense tables (line items, ledgers) where users may want to prioritize certain columns.
- **Column Hiding** — Supported on wide tables to let users tailor density to their role's needs (e.g., an Operator hiding financial columns they don't use).
- **Density** — A default density tuned for this product's data-heavy nature (compact-but-legible), with an optional comfortable/compact toggle on the heaviest tables.
- **Bulk Actions** — When row selection is enabled, a consistent contextual action bar appears (not a modal) summarizing the selection count and available bulk actions.
- **Row Selection** — A standard checkbox-in-first-column pattern, with a header checkbox for select-all-on-page, used only where bulk actions are actually meaningful for that entity.
- **Inline Actions** — A consistent kebab/context-menu pattern in the last column for row-level actions (View/Edit/Delete/etc.), rather than a row of individual icon buttons competing for attention.
- **Status Chips** — Every entity with a lifecycle state displays it as a Status Badge (Section 13) in a consistent column position (typically near the entity's name/number), never as plain colored text.
- **Search** — Table-level search is always scoped and labeled clearly (what fields it searches), distinct from Global Search's cross-entity scope.
- **Export** — Where offered, a consistent, clearly labeled export action in the table's action bar, respecting whatever filters are currently applied rather than always exporting the full unfiltered dataset.

---

## 10. Form Design

- **Validation** — Primarily inline and real-time for format-level errors (e.g., invalid GSTIN format) once a field has been interacted with; submission-time validation for cross-field and business-rule checks (e.g., allocation exceeding invoice balance).
- **Required Fields** — Marked with a single, consistent indicator; required-ness is never left to be discovered only via a submit-time error.
- **Optional Fields** — Explicitly labeled as optional where their required/optional status might otherwise be ambiguous, rather than relying purely on the absence of a required-marker.
- **Inline Errors** — Appear directly beneath the offending field, in the Danger color, phrased as plain corrective guidance ("Enter a GSTIN in the format ...") rather than a generic "Invalid input."
- **Server Errors** — Field-specific server-side validation errors map back to the specific field (mirroring inline client errors); non-field-specific server errors surface as a page-level Alert at the top of the form, never silently swallowed.
- **Success Messages** — Confirmed via Toast for quick actions (saved a draft) and via explicit page-state change for major actions (an issued invoice visibly becomes read-only/locked with its new status badge) — success is never communicated *only* by a toast that might be missed.
- **Autosave** — Used deliberately, only for genuinely low-stakes, frequently-interrupted drafting contexts, and always paired with a clear, persistent "saved"/"saving" indicator — never silent, and never used for the final, irreversible submission step of a lifecycle action (Issue, Post).
- **Draft Handling** — Draft-state records (e.g., a draft invoice) are visually distinguished (status badge, potentially muted chrome) from finalized records throughout the product, so a user can never mistake an in-progress draft for a committed, official record.

---

## 11. Charts

**Library:** Recharts, used consistently across every chart in the product.

**Chart Standards:**
- A single, consistent color-per-series mapping is used across all charts (via the semantic and neutral palettes from Section 3), so the same category means the same color everywhere a chart appears.
- Axes, gridlines, and labels use restrained neutral styling — the data is the visual content, not the chart chrome.
- All numeric axes and tooltips use the same tabular-numeral, exact-decimal formatting rules as the rest of the product (Section 4) — a chart is never the one place in the UI where a financial figure looks approximate.
- Tooltips on hover/focus, styled consistently with the Popover component.

**Chart Types & Usage:**
- **Line** — trends over time (e.g., revenue trend, receivables over time).
- **Bar** — comparison across discrete categories (e.g., sales by fish type, expenses by category).
- **Area** — cumulative or volume-emphasis trends over time (a variant of Line for emphasis, used sparingly to avoid visual noise).
- **Pie / Donut** — composition of a whole, used sparingly and only for a small number of categories (roughly five or fewer) — never for data better read as a table or bar chart.

**KPI Widgets / Financial Dashboard Widgets** — Built from the standardized Metric/KPI Card component (Section 8), optionally paired with a small inline sparkline-style chart for trend context; the number itself always remains the dominant visual element, with any chart as secondary support.

---

## 12. Navigation Design

**Sidebar** — Persistent, collapsible to an icon-only rail, grouped by section per the Navigation Philosophy in the Product Vision document (Dashboard / Masters / Operations / Finance / Reports / Administration / Settings), with clear active-route highlighting and role-based visibility (items a user cannot access are not shown).

**Topbar** — Houses tenant/company identity, the Global Search / Command Palette trigger, theme toggle, notifications, and the user menu — consistent placement on every page.

**Breadcrumb** — Present on all detail and edit pages beneath the page header, giving a clickable path back to the entity's list view.

**User Menu** — A consistent avatar-triggered dropdown (Profile, account-level actions, Logout), styled per the Dropdown/Menu standard.

**Search / Global Search / Command Palette** — A single ⌘K-triggered surface for jumping to any entity or action across the product, distinct from and complementary to per-table search (Section 9).

**Notifications** — A consistent bell icon with a badge count in the topbar, opening a panel of recent system notifications (overdue invoices, expiring licenses, etc. — per the Product Vision roadmap), styled per the Popover/Drawer standard depending on content volume.

**Quick Actions** — A consistent, discoverable entry point (e.g., in the topbar or command palette) for the handful of highest-frequency creation actions (new invoice, new payment, new trip), so common tasks never require multiple navigation hops.

---

## 13. Status System

Status is the single most important piece of information on most AquaLedger records, and is always communicated through the same consistent Status Badge component and consistent color mapping:

- **Draft** — Neutral/gray. Work in progress, not yet committed.
- **Issued** — Info/blue. Finalized and locked (invoices).
- **Posted** — Info/blue. Finalized and locked (purchase bills) — visually parallel to Issued, reinforcing that they are the same conceptual step on mirrored workflows.
- **Paid** — Success/green. Fully settled.
- **Partially Paid** — Warning/amber. Settled in part; still carries an outstanding balance.
- **Cancelled** — Muted danger (a subdued, desaturated red/gray, not an alarming full-strength red) — negative, but a resolved, intentional dead-end rather than an active problem.
- **Active** — Success/green, used for master-data status (a company, boat, or user in good standing).
- **Inactive** — Neutral/gray, mirroring Draft's visual weight to communicate "not currently in play."
- **Completed** — Success/green, used for finished operational records (e.g., a settled trip).
- **Pending** — Warning/amber, used for anything awaiting a next step or approval.
- **Success** (generic system feedback) — Success/green.
- **Warning** (generic system feedback) — Warning/amber.
- **Error** (generic system feedback) — Danger/red.

Two governing rules keep this system coherent as new entities are added: (1) the same status *concept* always uses the same color across every module (a warning is always amber, everywhere), and (2) an entity's full status vocabulary is always a small, closed set shown as a Status Badge — never free-form text standing in for state.

---

## 14. Motion

**Philosophy:** Motion in AquaLedger exists to explain a state change, not to entertain. Every animation should answer "where did this element come from or go to" — if an animation doesn't clarify that, it's cut. Durations are short and consistent; this is a tool optimized for repeat daily use, where animation delay compounds into real lost time over hundreds of interactions a day.

- **Hover** — Near-instant, subtle transitions (color/border shifts) with no perceptible delay.
- **Click / Press** — An immediate, brief visual acknowledgment (per Section 3's Pressed state) confirming the click registered before any async result returns.
- **Drawer** — Slides in from its anchored edge with a short, consistent duration; backdrop fades in concurrently.
- **Dialog** — A brief scale/fade-in paired with backdrop fade, short enough to feel immediate rather than ceremonial.
- **Table** — Row updates (e.g., after an inline edit or bulk action) use a brief highlight/fade rather than a jarring instant re-render, so users can track what changed.
- **Loading** — Skeleton loaders appear immediately (no delay-before-showing-loading-state) and are replaced by real content the instant it's available, with no artificial minimum display time.
- **Page Transitions** — Minimal and fast; navigating between pages should feel closer to instant than to a "transition" the user consciously perceives.
- **Skeletons** — Match the real content's shape and rhythm, with a subtle, consistent shimmer/pulse, never a generic gray box unrelated to what's loading.

Motion respects the user's reduced-motion preference system-wide (Section 16) — every animation described above degrades to an instant or near-instant state change when reduced motion is requested, with no loss of functional clarity.

---

## 15. Responsive Design

AquaLedger is a **desktop-first, data-dense operational tool**. Responsive behavior exists to keep the product usable outside the desktop context (a manager checking a dashboard on a tablet, a field operator on a phone at the dock), not to deliver an equally rich experience at every width.

- **Desktop** — The primary, fully-featured experience: full sidebar, multi-column layouts, wide data tables, side-by-side form/detail panels where useful.
- **Laptop** — Functionally identical to Desktop with tighter spacing and narrower default container widths.
- **Tablet** — Sidebar collapses to an icon rail or an on-demand drawer; multi-column layouts collapse to single-column; tables gain horizontal scroll rather than breaking their structure.
- **Mobile** — Reserved primarily for review/light-entry use cases (per the Product Vision's Field Staff persona and future mobile companion) rather than full parity with desktop; navigation collapses to a slide-out drawer with a hamburger trigger.

**Breakpoints:** A small, standard set of breakpoints (mobile / tablet / laptop / desktop) is used consistently across the entire product — no screen defines its own custom breakpoints.

**Navigation Behavior:** The sidebar's collapse behavior (full → icon rail → off-canvas drawer) is the single mechanism used everywhere; no screen invents an alternate navigation pattern for small widths.

**Tables on Small Screens:** Wide data tables gain horizontal scroll with a sticky first column (typically the entity's primary identifier) rather than being redesigned into stacked cards, preserving the table's scanability and this product's table-centric mental model even at narrow widths.

**Forms:** Multi-column form layouts collapse to a single column below the laptop breakpoint, preserving field grouping and order.

---

## 16. Accessibility

- **Keyboard Navigation** — Every interactive element and workflow (including the Command Palette, tables, and forms) is fully operable via keyboard alone, with a logical, predictable tab order.
- **Focus Management** — Focus is moved deliberately on major state changes (e.g., into a newly-opened Dialog, back to a triggering element on close) rather than left to default browser behavior, and is never trapped unintentionally.
- **ARIA** — Semantic roles, states, and labels are applied consistently across every instance of a given component, so assistive technology behavior is predictable product-wide rather than component-by-component.
- **Contrast** — All text, icons, and meaningful UI elements meet WCAG AA contrast minimums in both themes, including within colored Status Badges and chart elements.
- **Screen Readers** — Dynamic content changes (toast notifications, inline validation errors, table updates) are announced appropriately rather than silently updating the visual layer only.
- **Reduced Motion** — The system-level reduced-motion preference is honored globally, collapsing the animations described in Section 14 to instant or minimal-motion equivalents without any loss of information they were communicating.

---

## 17. Dark Mode

Dark mode is a **first-class theme**, designed as a full peer to light mode rather than an automatically-inverted afterthought — reflecting how much time users spend in this tool during long working sessions.

- **Dark Theme Philosophy** — Deep, desaturated neutral surfaces (never pure black) create a calm, low-glare working environment; semantic colors are softened/desaturated relative to their light-theme values so they read as correctly-weighted rather than neon against a dark background.
- **Contrast** — Text and meaningful UI elements maintain WCAG AA contrast against dark surfaces exactly as rigorously as in light mode — dark mode is never treated as a lower accessibility bar.
- **Charts** — Series colors, gridlines, and axis labels use their dark-theme-tuned values so charts remain immediately legible and correctly proportioned in emphasis, not simply light-mode charts placed on a dark background.
- **Tables** — Row striping/hover states, borders, and status badges all use dark-theme-appropriate contrast steps so dense tabular data remains scannable, which is arguably the single hardest and most important surface to get right in dark mode given how central tables are to this product.
- **Dialogs** — Elevation in dark mode is communicated primarily through a lighter surface step (since shadow reads less clearly on dark backgrounds) reinforced by a stronger backdrop dim.
- **Forms** — Input borders and focus states are tuned for sufficient contrast against dark surfaces, with placeholder and helper text kept legible rather than fading toward the background.

---

## 18. Component Naming Convention

A single, consistent naming vocabulary is used across design files, documentation, and code, so a name always means the same thing regardless of who wrote it:

- **Primary Button / Secondary Button / Outline Button / Danger Button** — button variants, never "blue button" or "red button."
- **Page Header** — the top-of-page title/breadcrumb/action-bar region.
- **Section Header** — a title/description region introducing a section within a page or form.
- **Section Card** — a bordered/surfaced container grouping related content within a page.
- **Entity Card** — a card representing a single record (e.g., a company or trip) in a card-based (non-tabular) list context.
- **Data Table** — the standardized table component described in Section 9, never referred to ad hoc as "grid" or "list view" in different places.
- **Metric Card / KPI Card** — the standardized dashboard number-display component from Section 8.
- **Status Badge** — the standardized lifecycle-state indicator from Section 13, never called "status pill," "status tag," or "chip" interchangeably — one name, one meaning.

This vocabulary is treated as canonical: new components are named by analogy to this list, not invented independently per feature.

---

## 19. Design Tokens

A **design token** is a named, reusable design decision — a single source of truth for one visual value — referenced everywhere that value is used, rather than that value being restated independently in each place. Tokens are what make every rule in this document enforceable in code rather than aspirational. This document defines the *categories* of tokens AquaLedger's system requires; concrete values (and their implementation as CSS variables, Tailwind config, or otherwise) belong to the frontend implementation layer, not this document.

- **Color Tokens** — semantic roles (Primary, Secondary, Accent, Success, Warning, Danger, Info, Neutral steps, Surface/Background/Border steps), each with a light-theme and dark-theme value, per Section 3.
- **Spacing Tokens** — the base unit and its multiples, per Section 5, referenced by every component's internal and external spacing.
- **Radius Tokens** — the small fixed set of corner-radius values, per Section 6, mapped consistently to component scale.
- **Typography Tokens** — font family assignments, the heading/body/caption size-and-weight scale, and line-height values, per Section 4.
- **Animation Tokens** — the small set of standard durations and easing curves, per Section 14, applied consistently rather than each component defining its own timing.
- **Elevation Tokens** — the small set of shadow definitions mapped to the elevation hierarchy in Section 6.

Every component in Section 8 is built exclusively from these token categories — no component introduces a one-off color, spacing value, radius, font size, duration, or shadow outside this system.

---

## 20. Design Principles Summary

AquaLedger's visual identity is deliberately quiet: a disciplined neutral palette carrying the weight of a data-dense product, a single confident accent color reserved for what actually matters, and typography and spacing systems precise enough that financial data reads as trustworthy on sight. Every choice in this document optimizes for the same outcome described in the Product Vision — a tool that feels like Linear, Stripe, Mercury, and Ramp because it is built with their same discipline: restraint over decoration, function over flourish, and system over one-off decisions.

**Consistency** is enforced structurally, not by convention alone — a small, closed set of components (Section 8), a small closed set of tokens (Section 19), and a canonical naming vocabulary (Section 18) mean there is exactly one correct way to build any given screen, not several equally-valid ones drifting apart over time.

**Scalability** comes from the same discipline: as new modules (Reports, Documents, OCR, AI) are added per the Product Vision roadmap, they inherit this system's components, tokens, and patterns rather than each introducing its own visual language.

**Maintainability** follows directly from tokens being the single source of truth for every visual decision — a future rebrand or theme refinement changes token values in one place and propagates everywhere, rather than requiring a hunt through every screen.

**Future-Proofing** is why this document deliberately avoids framework-specific and pixel-specific commitments: it defines *what* AquaLedger's design system must guarantee, so the specific implementation (Next.js, shadcn/ui, Tailwind, or whatever replaces them years from now) can evolve without the product ever losing the identity defined here.
