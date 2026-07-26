"use client";

import { useId } from "react";
import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface FormFieldRenderProps {
  id: string;
  describedBy: string | undefined;
  "aria-invalid": boolean;
}

export interface FormFieldProps {
  label?: ReactNode;
  description?: ReactNode;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  id?: string;
  children: ReactNode | ((props: FormFieldRenderProps) => ReactNode);
}

/**
 * The shared field chrome — Label, required indicator, Description, and
 * inline error message — used identically by every input in this library,
 * per `06_COMPONENT_LIBRARY.md` §4's category defaults ("every field has a
 * programmatically associated label," inline validation feedback). Every
 * typed input in this folder (`CurrencyInput`, `DatePicker`, ...) composes
 * this rather than re-implementing label/description/error markup itself —
 * it's also exported directly for a one-off field that wraps a control not
 * in this library.
 *
 * `children` may be a render function receiving the generated `id` and the
 * combined `aria-describedby` value, since `FormField` itself never renders
 * the control and so can't set those attributes on it directly.
 */
export function FormField({
  label,
  description,
  error,
  required,
  disabled,
  className,
  id: idProp,
  children,
}: FormFieldProps) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [descriptionId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("space-y-2", className)} data-disabled={disabled || undefined}>
      {label && (
        <Label htmlFor={id} className={cn(disabled && "opacity-50")}>
          {label}
          {required && (
            <span aria-hidden="true" className="text-destructive">
              *
            </span>
          )}
        </Label>
      )}

      {typeof children === "function"
        ? children({ id, describedBy, "aria-invalid": Boolean(error) })
        : children}

      {description && (
        <p id={descriptionId} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}

      {error && (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
