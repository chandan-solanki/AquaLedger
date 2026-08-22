"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Check, Monitor, Moon, Sun, type LucideIcon } from "lucide-react";

import { FormSection } from "@/components/form";
import { SettingsPageTemplate } from "@/components/templates/settings-page-template";
import { cn } from "@/lib/utils";

interface ThemeOption {
  value: "light" | "dark" | "system";
  label: string;
  description: string;
  icon: LucideIcon;
}

const THEME_OPTIONS: ThemeOption[] = [
  { value: "light", label: "Light", description: "Always use the light appearance.", icon: Sun },
  { value: "dark", label: "Dark", description: "Always use the dark appearance.", icon: Moon },
  {
    value: "system",
    label: "System",
    description: "Follow your device or operating system preference.",
    icon: Monitor,
  },
];

/**
 * A first-class settings UI over the exact mechanism ThemeSwitcher (the
 * topbar toggle) already uses - next-themes' useTheme()/setTheme(),
 * persisted to localStorage under providers/theme-provider.tsx's
 * storageKey. Sprint 16 Session 5's audit found this already persists
 * correctly across reloads and resolves "system" live, and is
 * deliberately browser/device-scoped (the ThemeProvider sits above
 * AuthProvider and applies even on /login) rather than tied to the
 * authenticated user - no product requirement calls for cross-device
 * sync, so this page adds no backend, no database column, and no second
 * persistence layer; it is a second entry point onto the same one.
 *
 * `theme` is next-themes' own SELECTED value - "system" stays "system"
 * here, it is never silently resolved to "light"/"dark" the way
 * `resolvedTheme` (not used on this page) would be.
 */
export function AppearanceSettingsPage() {
  const { theme, setTheme } = useTheme();
  // Same reason ThemeSwitcher waits for mount: next-themes only knows the
  // real stored value after the client reads localStorage, so rendering
  // the selected state before that would either guess wrong or mismatch
  // what the server rendered.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <SettingsPageTemplate
      title="Appearance"
      description="Customize how the application looks on this device."
      isLoading={!mounted}
    >
      <FormSection title="Theme">
        <fieldset className="grid gap-3 sm:grid-cols-3">
          <legend className="sr-only">Theme</legend>
          {THEME_OPTIONS.map(({ value, label, description, icon: Icon }) => {
            const selected = theme === value;
            return (
              <label
                key={value}
                className={cn(
                  "flex cursor-pointer flex-col gap-2 rounded-xl border p-4 transition-colors",
                  "has-focus-visible:ring-2 has-focus-visible:ring-ring has-focus-visible:ring-offset-2",
                  selected ? "border-primary bg-primary/5" : "border-border hover:bg-accent"
                )}
              >
                <input
                  type="radio"
                  name="appearance-theme"
                  value={value}
                  checked={selected}
                  onChange={() => setTheme(value)}
                  className="sr-only"
                />
                <span className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 font-medium text-foreground">
                    <Icon className="size-4" aria-hidden="true" />
                    {label}
                  </span>
                  {selected && <Check className="size-4 text-primary" aria-hidden="true" />}
                </span>
                <span className="text-sm text-muted-foreground">{description}</span>
              </label>
            );
          })}
        </fieldset>
      </FormSection>
    </SettingsPageTemplate>
  );
}
