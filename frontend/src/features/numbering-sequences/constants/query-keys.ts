/** A read-only, tenant-wide snapshot - no id/detail variants. */
export const numberingSequenceKeys = {
  all: () => ["numbering-sequences"] as const,
  list: () => [...numberingSequenceKeys.all(), "list"] as const,
};
