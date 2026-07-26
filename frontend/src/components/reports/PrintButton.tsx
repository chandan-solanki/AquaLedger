"use client";

import { Printer } from "lucide-react";

import { ToolbarButton } from "@/components/layout/action-buttons";

export interface PrintButtonProps {
  /** Defaults to the browser's native `window.print()` — override only if a future page needs a print-specific view first. No PDF/export generation happens here either way. */
  onPrint?: () => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export function PrintButton({ onPrint, label = "Print", disabled, className }: PrintButtonProps) {
  return (
    <ToolbarButton onClick={onPrint ?? (() => window.print())} disabled={disabled} className={className}>
      <Printer />
      {label}
    </ToolbarButton>
  );
}
