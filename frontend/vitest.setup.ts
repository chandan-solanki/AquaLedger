import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver or scrollIntoView - cmdk (the Command palette behind
// Combobox/AsyncSelect) requires both.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
if (typeof Element.prototype.scrollIntoView === "undefined") {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}
