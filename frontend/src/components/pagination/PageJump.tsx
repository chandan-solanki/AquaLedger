"use client";

import { useState } from "react";
import type { FormEvent } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface PageJumpProps {
  totalPages: number;
  onPageChange: (page: number) => void;
  label?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
}

/**
 * A "Go to page" input — commits on submit (Enter), out-of-range values are
 * simply ignored rather than clamped, so a stray keystroke never silently
 * jumps somewhere the user didn't intend.
 */
export function PageJump({
  totalPages,
  onPageChange,
  label = "Go to",
  disabled = false,
  id = "page-jump-input",
  className,
}: PageJumpProps) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = Number(value);
    if (Number.isFinite(target) && target >= 1 && target <= totalPages) {
      onPageChange(target);
    }
    setValue("");
  }

  return (
    <form onSubmit={handleSubmit} className={cn("flex items-center gap-1.5", className)}>
      {label && (
        <label htmlFor={id} className="text-sm whitespace-nowrap text-muted-foreground">
          {label}
        </label>
      )}
      <Input
        id={id}
        type="number"
        min={1}
        max={totalPages}
        disabled={disabled}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        className="h-8 w-16 px-2"
        aria-label="Jump to page"
      />
    </form>
  );
}
