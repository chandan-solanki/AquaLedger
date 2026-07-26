/**
 * The app-wide default display/entry format for dates (day-first, matching
 * this user base's convention) — shared by every date-displaying/entry
 * component (`DatePicker`, `DateRangePicker`, `DateRangeHeader`,
 * `ReportHeader`, …) so a future locale change is a one-line edit instead of
 * a find-and-replace across the component library.
 */
export const DEFAULT_DATE_FORMAT = "dd/MM/yyyy";
export const DEFAULT_DATETIME_FORMAT = "dd/MM/yyyy, HH:mm";
