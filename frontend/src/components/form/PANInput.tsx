"use client";

import type { ChangeEvent, ComponentProps } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { FormField } from "./FormField";

export interface PANInputProps
  extends Omit<ComponentProps<"input">, "type" | "className"> {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  containerClassName?: string;
  className?: string;
}

/**
 * Text Input configured for PAN entry — auto-uppercased as the user
 * types (PAN is canonically upper-case), rendered in the monospace family
 * reserved for identifier/code content, mirroring `GSTINInput` exactly. The
 * 10-character format check itself is the owning form's Zod schema /
 * backend's job — this component only shapes the raw keystroke, it never
 * validates.
 */
export function PANInput({
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
}: PANInputProps) {
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
          maxLength={10}
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
