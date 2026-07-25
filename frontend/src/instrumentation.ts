export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    // Fails fast at server startup if required environment variables are
    // missing/invalid, rather than surfacing as a runtime undefined deep in
    // a feature (07_FRONTEND_ARCHITECTURE.md §26).
    await import("@/config/env");
  }
}
