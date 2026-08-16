/**
 * Triggers a real browser download of a same-origin `url` via a plain
 * anchor click, not fetch+blob - the browser handles the response's own
 * `Content-Disposition: attachment` header natively, and a same-origin
 * BFF route carries the session's httpOnly cookies along automatically,
 * exactly like any other authenticated navigation. Shared by every
 * feature that downloads a backend-rendered file (reports/statements,
 * Sprint 11; invoice PDFs, Sprint 12 Session 2) rather than each
 * duplicating this same anchor-click mechanism.
 */
export function downloadUrl(url: string): void {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}
