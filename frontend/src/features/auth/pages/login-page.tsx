import { Suspense } from "react";
import { Fish } from "lucide-react";

import { LoginForm } from "@/features/auth/components/login-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function LoginPage() {
  return (
    <div className="flex min-h-svh w-full items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-3 text-center">
          {/* Logo placeholder — replaced with the real AquaLedger mark later. */}
          <div className="flex size-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Fish className="size-6" aria-hidden />
          </div>
          <div>
            <h1 className="text-lg font-semibold">AquaLedger</h1>
            <p className="text-sm text-muted-foreground">Sign in to your account</p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Log in</CardTitle>
            <CardDescription>Enter your email and password to continue.</CardDescription>
          </CardHeader>
          <CardContent>
            <Suspense fallback={null}>
              <LoginForm />
            </Suspense>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
