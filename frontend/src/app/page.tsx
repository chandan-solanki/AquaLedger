import { redirect } from "next/navigation";

// Forced dynamic: a statically-prerendered redirect here was observed being
// served from Next.js's static cache incorrectly (a stale/404 response)
// rather than issuing the redirect on every request.
export const dynamic = "force-dynamic";

export default function RootPage() {
  // middleware.ts branches this to /login when unauthenticated.
  redirect("/dashboard");
}
