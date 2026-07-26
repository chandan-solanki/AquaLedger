"use client";

import type { ComponentProps } from "react";

import { Input } from "@/components/ui/input";

import { FormField } from "./FormField";

export interface EmailInputProps
  extends Omit<ComponentProps<"input">, "type" | "className"> {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  containerClassName?: string;
  className?: string;
}

/**
 * Text Input configured for email entry — `type="email"` gives native
 * keyboard/autofill hints; the actual format check (and its error message)
 * is the owning form's Zod schema's job, per `06_COMPONENT_LIBRARY.md` §4 /
 * `07_FRONTEND_ARCHITECTURE.md` §12 — this component supplies the input
 * affordance, not validation logic.
 */
export function EmailInput({
  label,
  description,
  error,
  required,
  disabled,
  containerClassName,
  className,
  id,
  ...props
}: EmailInputProps) {
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
          type="email"
          inputMode="email"
          autoComplete="email"
          disabled={disabled}
          aria-invalid={ariaInvalid}
          aria-describedby={describedBy}
          aria-required={required}
          className={className}
          {...props}
        />
      )}
    </FormField>
  );
}
