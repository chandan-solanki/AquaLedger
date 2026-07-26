"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface StatusFilterOption<TValue extends string = string> {
  value: TValue;
  label: string;
}

interface StatusFilterSingleProps<TValue extends string = string> {
  multiple?: false;
  value?: TValue;
  onChange: (value: TValue | undefined) => void;
}

interface StatusFilterMultiProps<TValue extends string = string> {
  multiple: true;
  value: TValue[];
  onChange: (value: TValue[]) => void;
}

export type StatusFilterProps<TValue extends string = string> = {
  label?: string;
  options: StatusFilterOption<TValue>[];
  className?: string;
} & (StatusFilterSingleProps<TValue> | StatusFilterMultiProps<TValue>);

/**
 * A generic status/lifecycle-vocabulary filter, per `06_COMPONENT_LIBRARY.md`
 * §6 — genuinely entity-agnostic: it renders whatever `options` it's given
 * (Invoice Status's vocabulary, Trip Status's, a future module's — never a
 * hardcoded set), single- or multi-select via the `multiple` prop.
 */
export function StatusFilter<TValue extends string = string>(props: StatusFilterProps<TValue>) {
  const { options, label, className } = props;

  function isSelected(optionValue: TValue): boolean {
    return props.multiple ? props.value.includes(optionValue) : props.value === optionValue;
  }

  function toggle(optionValue: TValue) {
    if (props.multiple) {
      const next = props.value.includes(optionValue)
        ? props.value.filter((v) => v !== optionValue)
        : [...props.value, optionValue];
      props.onChange(next);
    } else {
      props.onChange(props.value === optionValue ? undefined : optionValue);
    }
  }

  return (
    <div className={cn("flex flex-col gap-2", className)} role="group" aria-label={label}>
      {label && <span className="text-sm font-medium">{label}</span>}
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => {
          const selected = isSelected(option.value);
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={selected}
              onClick={() => toggle(option.value)}
              className="rounded-full outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <Badge
                variant={selected ? "default" : "outline"}
                className="cursor-pointer px-3 py-1 select-none"
              >
                {option.label}
              </Badge>
            </button>
          );
        })}
      </div>
    </div>
  );
}
