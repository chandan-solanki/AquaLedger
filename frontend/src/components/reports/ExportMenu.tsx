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
  /** Restricts which menu items render — defaults to all three. Statements (TASKS.md Sprint 11 Session 5 Phase C) pass `["excel", "pdf"]` since CSV is not a supported statement format. */
  formats?: ExportFormat[];
}

const EXPORT_OPTIONS: { format: ExportFormat; label: string; icon: LucideIcon }[] = [
  { format: "csv", label: "Export as CSV", icon: FileText },
  { format: "excel", label: "Export as Excel", icon: FileSpreadsheet },
  { format: "pdf", label: "Export as PDF", icon: FileDown },
];

/** The Export trigger for a Report/List page toolbar — UI only, per this session's scope; no CSV/Excel/PDF generation happens here. */
export function ExportMenu({
  onExport,
  disabled,
  label = "Export",
  className,
  formats,
}: ExportMenuProps) {
  const options = formats
    ? EXPORT_OPTIONS.filter((option) => formats.includes(option.format))
    : EXPORT_OPTIONS;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <ToolbarButton disabled={disabled} className={className}>
          <Download />
          {label}
        </ToolbarButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {options.map(({ format: exportFormat, label: optionLabel, icon: Icon }) => (
          <DropdownMenuItem key={exportFormat} onClick={() => onExport(exportFormat)}>
            <Icon />
            {optionLabel}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
