"use client";

import type { ChangeEvent, ComponentProps } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { FormField } from "./FormField";

export interface GSTINInputProps
  extends Omit<ComponentProps<"input">, "type" | "className"> {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  containerClassName?: string;
  className?: string;
}

/**
 * Text Input configured for GSTIN entry — auto-uppercased as the user
 * types (GSTIN is canonically upper-case) and rendered in the monospace
 * family reserved for identifier/code content, per `02_DESIGN_SYSTEM.md`
 * §4's "Monospace Usage" rule. The 15-character format check itself (and
 * duplicate-GSTIN detection) is the owning form's Zod schema / backend's
 * job, per `04_USER_FLOWS.md` §4 — this component only shapes the raw
 * keystroke, it never validates.
 */
export function GSTINInput({
  label,
  description,
  error,
  required,
  disabled,
  onChange,
  containerClassName,
  className,
  id,
  ...props
}: GSTINInputProps) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const upper = event.target.value.toUpperCase();
    if (upper !== event.target.value) {
      event.target.value = upper;
    }
    onChange?.(event);
  }

  return (
    <FormField
      label={label}
      description={description}
      error={error}
      required={required}
      disabled={disabled}
      id={id}
      className={containerClassName}
    >
      {({ id: fieldId, describedBy, "aria-invalid": ariaInvalid }) => (
        <Input
          id={fieldId}
          type="text"
          maxLength={15}
          autoCapitalize="characters"
          disabled={disabled}
          aria-invalid={ariaInvalid}
          aria-describedby={describedBy}
          aria-required={required}
          onChange={handleChange}
          className={cn("font-mono uppercase", className)}
          {...props}
        />
      )}
    </FormField>
  );
}
