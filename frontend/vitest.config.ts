import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Sprint 15 Session 3 - the first frontend test runner this project has
 * had. Deliberately minimal: Vitest + React Testing Library, the standard
 * pairing for a Next.js 15 App Router codebase, config kept to what's
 * actually needed (jsdom environment, the same `@/*` path alias tsconfig.json
 * declares - resolved natively by Vite 7/Vitest 4 rather than the
 * `vite-tsconfig-paths` plugin - and jest-dom matchers). No coverage
 * thresholds or CI wiring added - that's a separate decision for whoever
 * owns the test strategy going forward.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    tsconfigPaths: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
});
