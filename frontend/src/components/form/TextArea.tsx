"use client";

import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

import { FormField } from "./FormField";

export interface TextAreaProps extends Omit<ComponentProps<"textarea">, "className"> {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  containerClassName?: string;
  className?: string;
}

/**
 * Multi-line free text, sized to its expected content length — address
 * fields, future Notes, per `06_COMPONENT_LIBRARY.md` §4. Shares the same
 * height/padding/border/focus-ring language as `Input` (`02_DESIGN_SYSTEM.md`
 * §8's "Textarea follows the same visual language as text inputs") rather
 * than defining its own.
 */
export function TextArea({
  label,
  description,
  error,
  required,
  disabled,
  readOnly,
  containerClassName,
  className,
  id,
  rows = 4,
  ...props
}: TextAreaProps) {
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
        <textarea
          id={fieldId}
          rows={rows}
          disabled={disabled}
          readOnly={readOnly}
          aria-invalid={ariaInvalid}
          aria-describedby={describedBy}
          aria-required={required}
          className={cn(
            "flex w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30",
            "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
            "aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40",
            className
          )}
          {...props}
        />
      )}
    </FormField>
  );
}
