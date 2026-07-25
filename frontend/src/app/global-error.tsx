"use client";

/**
 * Catches an error thrown by the root layout itself — a case app/error.tsx
 * cannot handle, since it renders *inside* that layout. Per Next.js's own
 * requirement, this file must render its own <html>/<body> (it replaces the
 * root layout entirely) and is kept deliberately minimal and
 * dependency-free: no AppProviders, no toast, no theme — none of that is
 * guaranteed to be mounted when this fires.
 */
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif" }}>
        <div
          style={{
            display: "flex",
            minHeight: "100vh",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "1rem",
            padding: "1.5rem",
            textAlign: "center",
          }}
        >
          <div>
            <h1 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>
              Something went wrong
            </h1>
            <p style={{ maxWidth: "24rem", color: "#6b7280", fontSize: "0.875rem" }}>
              The application failed to load. Please try again.
            </p>
          </div>
          <button
            onClick={reset}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "0.375rem",
              border: "1px solid #d1d5db",
              background: "#111827",
              color: "#fff",
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            Retry
          </button>
        </div>
      </body>
    </html>
  );
}
