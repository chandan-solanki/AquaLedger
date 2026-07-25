"use client";

import { useTheme } from "next-themes";
import { Toaster, type ToasterProps } from "sonner";

export function ToastProvider() {
  const { resolvedTheme } = useTheme();

  return (
    <Toaster
      theme={resolvedTheme as ToasterProps["theme"]}
      position="top-right"
      richColors
      closeButton
    />
  );
}
