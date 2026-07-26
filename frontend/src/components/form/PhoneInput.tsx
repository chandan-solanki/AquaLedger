"use client";

import type { ComponentProps } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { FormField } from "./FormField";

export interface PhoneInputProps
  extends Omit<ComponentProps<"input">, "type" | "className"> {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  /** e.g. "+91" — rendered as a fixed leading affix, per `06_COMPONENT_LIBRARY.md` §4's "optional country-code affix." */
  countryCode?: string;
  containerClassName?: string;
  className?: string;
}

/**
 * Text Input configured for phone entry, with an optional country-code
 * affix — Company/Supplier contact fields, Boat captain contact, per
 * `06_COMPONENT_LIBRARY.md` §4. Format validation is the owning form's Zod
 * schema's job, not this component's.
 */
export function PhoneInput({
  label,
  description,
  error,
  required,
  disabled,
  countryCode,
  containerClassName,
  className,
  id,
  ...props
}: PhoneInputProps) {
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
        <div className="relative">
          {countryCode && (
            <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-sm text-muted-foreground">
              {countryCode}
            </span>
          )}
          <Input
            id={fieldId}
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            disabled={disabled}
            aria-invalid={ariaInvalid}
            aria-describedby={describedBy}
            aria-required={required}
            className={cn(countryCode && "pl-11", className)}
            {...props}
          />
        </div>
      )}
    </FormField>
  );
}
