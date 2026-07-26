"use client";

import { Download, FileDown, FileSpreadsheet, FileText } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ToolbarButton } from "@/components/layout/action-buttons";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export type ExportFormat = "csv" | "excel" | "pdf";

export interface ExportMenuProps {
  /** UI only — no file is generated here; the caller wires this to its own export request. */
  onExport: (format: ExportFormat) => void;
  disabled?: boolean;
  label?: string;
  className?: string;
}

const EXPORT_OPTIONS: { format: ExportFormat; label: string; icon: LucideIcon }[] = [
  { format: "csv", label: "Export as CSV", icon: FileText },
  { format: "excel", label: "Export as Excel", icon: FileSpreadsheet },
  { format: "pdf", label: "Export as PDF", icon: FileDown },
];

/** The Export trigger for a Report/List page toolbar — UI only, per this session's scope; no CSV/Excel/PDF generation happens here. */
export function ExportMenu({ onExport, disabled, label = "Export", className }: ExportMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <ToolbarButton disabled={disabled} className={className}>
          <Download />
          {label}
        </ToolbarButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {EXPORT_OPTIONS.map(({ format: exportFormat, label: optionLabel, icon: Icon }) => (
          <DropdownMenuItem key={exportFormat} onClick={() => onExport(exportFormat)}>
            <Icon />
            {optionLabel}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
