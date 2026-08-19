"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { AlertCircle, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/features/auth/hooks/use-auth";
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas/login-schema";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";
import type { ApiError } from "@/types/api";

const DEFAULT_REDIRECT = "/dashboard";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [formError, setFormError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setFormError(null);

    try {
      await login(values);
      const next = searchParams.get("next");
      router.push(next && next.startsWith("/") ? next : DEFAULT_REDIRECT);
    } catch (error) {
      const apiError = error as ApiError;

      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<LoginFormValues>(apiError.fieldErrors, setError);
        return;
      }

      setFormError(apiError.message || "Unable to log in. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
      {formError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? "email-error" : undefined}
          {...register("email")}
        />
        {errors.email && (
          <p id="email-error" className="text-sm text-destructive">
            {errors.email.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Password</Label>
          <button
            type="button"
            // Placeholder only this session — the real flow ships with
            // 05_PAGE_CATALOG.md §1's dedicated Forgot/Reset Password pages.
            onClick={() => toast.info("Forgot password flow is coming soon.")}
            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            Forgot password?
          </button>
        </div>
        <div className="relative">
          <Input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            placeholder="••••••••"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : undefined}
            className="pr-10"
            {...register("password")}
          />
          <button
            type="button"
            onClick={() => setShowPassword((previous) => !previous)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
          >
            {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
        {errors.password && (
          <p id="password-error" className="text-sm text-destructive">
            {errors.password.message}
          </p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Checkbox
          id="rememberMe"
          checked={watch("rememberMe")}
          onCheckedChange={(checked) => setValue("rememberMe", checked === true)}
        />
        <Label htmlFor="rememberMe" className="font-normal text-muted-foreground">
          Remember me
        </Label>
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
        {isSubmitting ? "Logging in…" : "Log in"}
      </Button>
    </form>
  );
}
